"""
tests/test_orchestrator.py
───────────────────────────
Tests for every path in the Orchestrator decision tree,
budget manager, and full pipeline integration.

Run with: cd backend && python -m pytest tests/ -v
"""

import asyncio
import pytest

from core.models import (
    AgentResult,
    CompletionStatus,
    OrchestratorAction,
    TaskComplexity,
    TokenBudget,
)
from core.budget_manager import TokenBudgetManager
from core.orchestrator import Orchestrator, COVERAGE_THRESHOLDS
from tests.conftest import make_result


# ─────────────────────────────────────────────
# Decision Tree Tests
# ─────────────────────────────────────────────

class TestOrchestratorDecisionTree:

    def test_complete_result_advances(self, orchestrator):
        """COMPLETE -> always ADVANCE."""
        result = make_result(CompletionStatus.COMPLETE)
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.ADVANCE
        assert decision.result is result

    def test_partial_safe_high_coverage_continues_with_warning(self, orchestrator):
        """PARTIAL_SAFE at 80%+ -> CONTINUE_WITH_WARNING."""
        result = make_result(CompletionStatus.PARTIAL_SAFE, processed=4, total=5)
        assert result.coverage == 0.8
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.CONTINUE_WITH_WARNING
        assert decision.warning is not None
        assert "80%" in decision.warning

    def test_partial_safe_medium_coverage_retries_from_checkpoint(self, orchestrator):
        """PARTIAL_SAFE at 60% with checkpoint -> RETRY_FROM_CHECKPOINT."""
        checkpoint = {"completed_segments": ["seg_0", "seg_1", "seg_2"], "results": []}
        result = make_result(
            CompletionStatus.PARTIAL_SAFE,
            processed=3, total=5,
            checkpoint=checkpoint,
        )
        assert result.coverage == 0.6
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.RETRY_FROM_CHECKPOINT
        assert decision.checkpoint == checkpoint

    def test_partial_safe_medium_coverage_no_checkpoint_retries_scratch(self, orchestrator):
        """PARTIAL_SAFE at 60% without checkpoint -> RETRY_FROM_SCRATCH."""
        result = make_result(CompletionStatus.PARTIAL_SAFE, processed=3, total=5)
        assert result.coverage == 0.6
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.RETRY_FROM_SCRATCH

    def test_partial_safe_low_coverage_replans(self, orchestrator):
        """PARTIAL_SAFE under 50% -> REPLAN."""
        result = make_result(CompletionStatus.PARTIAL_SAFE, processed=2, total=5)
        assert result.coverage == 0.4
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.REPLAN

    def test_partial_unsafe_always_discarded(self, orchestrator):
        """PARTIAL_UNSAFE -> RETRY_FROM_SCRATCH."""
        result = make_result(CompletionStatus.PARTIAL_UNSAFE)
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.RETRY_FROM_SCRATCH

    def test_partial_unsafe_after_max_retries_escalates(self, orchestrator):
        """PARTIAL_UNSAFE after max retries -> ESCALATE_TO_HUMAN."""
        orchestrator._retry_counts["audience_intel"] = 2
        result = make_result(CompletionStatus.PARTIAL_UNSAFE)
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.ESCALATE_TO_HUMAN

    def test_budget_exceeded_with_checkpoint_retries(self, orchestrator):
        """BUDGET_EXCEEDED + checkpoint -> RETRY_FROM_CHECKPOINT."""
        checkpoint = {"completed_segments": ["seg_0", "seg_1"]}
        result = make_result(CompletionStatus.BUDGET_EXCEEDED, checkpoint=checkpoint)
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.RETRY_FROM_CHECKPOINT

    def test_budget_exceeded_no_checkpoint_escalates(self, orchestrator):
        """BUDGET_EXCEEDED without checkpoint -> ESCALATE_TO_HUMAN."""
        result = make_result(CompletionStatus.BUDGET_EXCEEDED)
        decision = orchestrator.decide(result)
        assert decision.action == OrchestratorAction.ESCALATE_TO_HUMAN

    def test_failed_retries_then_escalates(self, orchestrator):
        """FAILED -> retry up to max, then ESCALATE."""
        result = make_result(CompletionStatus.FAILED, error="API timeout")

        d1 = orchestrator.decide(result)
        assert d1.action == OrchestratorAction.RETRY_FROM_SCRATCH

        d2 = orchestrator.decide(result)
        assert d2.action == OrchestratorAction.RETRY_FROM_SCRATCH

        d3 = orchestrator.decide(result)
        assert d3.action == OrchestratorAction.ESCALATE_TO_HUMAN

    def test_retry_count_increments_per_agent(self, orchestrator):
        """Retry counter increments per agent_id, not globally."""
        result_a = make_result(CompletionStatus.FAILED, agent_id="analytics")
        result_b = make_result(CompletionStatus.FAILED, agent_id="meta_ads")

        orchestrator.decide(result_a)
        orchestrator.decide(result_b)

        assert orchestrator._retry_counts["analytics"] == 1
        assert orchestrator._retry_counts["meta_ads"] == 1

    def test_complete_result_has_no_warning(self, orchestrator):
        """COMPLETE results should never carry warnings."""
        result = make_result(CompletionStatus.COMPLETE)
        decision = orchestrator.decide(result)
        assert decision.warning is None


# ─────────────────────────────────────────────
# Budget Manager Tests
# ─────────────────────────────────────────────

class TestTokenBudgetManager:

    def test_assign_returns_budget(self, budget_manager):
        budget = budget_manager.assign("audience_intel")
        assert isinstance(budget, TokenBudget)
        assert budget.agent_id == "audience_intel"
        assert budget.max_input_tokens > 0

    def test_complexity_scales_budget(self, budget_manager):
        low = budget_manager.assign("audience_intel", TaskComplexity.LOW)
        norm = budget_manager.assign("audience_intel", TaskComplexity.NORMAL)
        high = budget_manager.assign("audience_intel", TaskComplexity.HIGH)
        assert low.max_input_tokens < norm.max_input_tokens < high.max_input_tokens

    def test_unknown_agent_raises(self, budget_manager):
        with pytest.raises(ValueError, match="Unknown agent"):
            budget_manager.assign("fake_agent_xyz")

    def test_retry_budget_is_larger(self, budget_manager):
        original = budget_manager.assign("analytics")
        retry = budget_manager.assign_retry_budget(original, retry_number=1)
        assert retry.max_input_tokens > original.max_input_tokens

    def test_retry_budget_grows_with_retry_number(self, budget_manager):
        original = budget_manager.assign("analytics")
        retry1 = budget_manager.assign_retry_budget(original, retry_number=1)
        retry2 = budget_manager.assign_retry_budget(original, retry_number=2)
        assert retry2.max_input_tokens > retry1.max_input_tokens

    def test_safety_threshold_is_nonzero(self, budget_manager):
        budget = budget_manager.assign("audience_intel")
        assert budget.safety_threshold > 0

    def test_budget_allows_when_safe(self, budget_manager):
        budget = budget_manager.assign("audience_intel")
        assert budget.is_safe_to_start_unit(0, 1_000)

    def test_budget_blocks_when_too_close(self, budget_manager):
        budget = budget_manager.assign("audience_intel")
        tokens_used = budget.max_input_tokens - budget.safety_threshold + 100
        assert not budget.is_safe_to_start_unit(tokens_used, 4_000)

    def test_cost_estimate_is_positive(self, budget_manager):
        budget = budget_manager.assign("meta_ads")
        cost = budget_manager.estimate_cost(budget)
        assert cost > 0.0

    def test_pipeline_cost_estimate(self, budget_manager):
        estimate = budget_manager.estimate_pipeline_cost(TaskComplexity.NORMAL)
        assert "total_usd" in estimate
        assert "per_agent" in estimate
        assert estimate["total_usd"] > 0


# ─────────────────────────────────────────────
# Integration — Full Pipeline
# ─────────────────────────────────────────────

class TestFullPipeline:

    @pytest.mark.asyncio
    async def test_pipeline_completes(self, orchestrator):
        """End-to-end pipeline should complete without errors."""
        from agents.registry import build_agent_registry

        registry = build_agent_registry()
        state = await orchestrator.run_pipeline(
            goal="Optimize ROAS across all platforms for the next 7 days",
            agent_registry=registry,
            complexity=TaskComplexity.NORMAL,
        )

        assert state.completed
        assert state.total_tokens_used > 0
        assert "orchestrator" in state.results
        assert "audience_intel" in state.results
        assert "reporting" in state.results

    @pytest.mark.asyncio
    async def test_pipeline_handles_agent_failure_gracefully(self, orchestrator):
        """Pipeline should not crash if one agent fails."""
        from agents.registry import build_agent_registry

        registry = build_agent_registry()

        async def failing_analytics(task, budget):
            return AgentResult(
                agent_id="analytics",
                status=CompletionStatus.FAILED,
                data={},
                error="Simulated GA4 API timeout",
            )

        registry["analytics"] = failing_analytics
        state = await orchestrator.run_pipeline(
            goal="Test failure recovery",
            agent_registry=registry,
            complexity=TaskComplexity.LOW,
        )

        assert "audience_intel" in state.results

    @pytest.mark.asyncio
    async def test_partial_result_propagates_warning(self, orchestrator):
        """Partial agent results should generate warnings in pipeline state."""
        from agents.registry import build_agent_registry

        registry = build_agent_registry()

        async def partial_audience(task, budget):
            return AgentResult(
                agent_id="audience_intel",
                status=CompletionStatus.PARTIAL_SAFE,
                data={"segments": [{"segment_id": "past_customers", "roas_7d": 8.2, "verdict": "scale"}]},
                items_processed=4,
                items_total=5,
                tokens_used=18_000,
                checkpoint={"completed_segments": ["past_customers"]},
            )

        registry["audience_intel"] = partial_audience
        state = await orchestrator.run_pipeline(
            goal="Test partial propagation",
            agent_registry=registry,
            complexity=TaskComplexity.LOW,
        )

        assert len(state.warnings) > 0
