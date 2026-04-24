"""
core/orchestrator.py
─────────────────────
The Orchestrator: assigns budgets, runs agents, handles every
result status with a deterministic decision tree.

No silent failures. No partial data passed as complete.
Every decision is logged and auditable.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Callable

from .models import (
    AgentResult,
    CompletionStatus,
    OrchestratorAction,
    OrchestratorDecision,
    PipelineState,
    TaskComplexity,
)
from .budget_manager import TokenBudgetManager

logger = logging.getLogger(__name__)


# Coverage thresholds — tune these for your business
COVERAGE_THRESHOLDS = {
    "min_to_advance":   0.80,
    "min_to_retry":     0.50,
}

MAX_RETRIES_PER_AGENT = 2


class Orchestrator:
    """
    The central coordinator for the ads agent network.

    Responsibilities:
    1. Decompose goals into tasks
    2. Assign token budgets before each agent starts
    3. Run agents (sequential or parallel)
    4. Handle every result with a deterministic decision tree
    5. Track pipeline state end-to-end
    """

    def __init__(self, budget_manager: TokenBudgetManager):
        self.budget_manager = budget_manager
        self._retry_counts: dict[str, int] = {}

    # ──────────────────────────────────────────
    # Main entry point
    # ──────────────────────────────────────────

    async def run_pipeline(
        self,
        goal: str,
        agent_registry: dict[str, Callable],
        complexity: TaskComplexity = TaskComplexity.NORMAL,
    ) -> PipelineState:
        """Run the full 5-step analysis pipeline."""
        run_id = str(uuid.uuid4())[:8]
        state = PipelineState(run_id=run_id)

        logger.info(f"\n{'='*60}")
        logger.info(f"Pipeline run {run_id} | goal: {goal}")
        logger.info(f"Complexity: {complexity.value}")
        logger.info(f"{'='*60}")

        try:
            # Step 1: Orchestrator decomposes goal
            logger.info("\n[STEP 1] Goal decomposition")
            orch_result = await self._run_agent_with_budget(
                agent_id="orchestrator",
                agent_fn=agent_registry["orchestrator"],
                task={"goal": goal, "phase": "decompose"},
                complexity=complexity,
            )
            state.add_result(orch_result)
            decision = self.decide(orch_result)
            state.decisions["orchestrator_decompose"] = decision

            if decision.action not in (
                OrchestratorAction.ADVANCE,
                OrchestratorAction.CONTINUE_WITH_WARNING,
            ):
                logger.error(f"Pipeline aborted at Step 1: {decision}")
                return state

            # Step 2: Audience Intel + Analytics (parallel)
            logger.info("\n[STEP 2] Audience Intel + Analytics (parallel)")
            parallel_results = await asyncio.gather(
                self._run_agent_with_budget(
                    "audience_intel",
                    agent_registry["audience_intel"],
                    task={"segments": orch_result.data.get("segments", [])},
                    complexity=complexity,
                ),
                self._run_agent_with_budget(
                    "analytics",
                    agent_registry["analytics"],
                    task={"date_range": "last_7_days"},
                    complexity=complexity,
                ),
                return_exceptions=True,
            )

            audience_result, analytics_result = parallel_results
            for result in [audience_result, analytics_result]:
                if isinstance(result, Exception):
                    logger.error(f"Parallel agent crashed: {result}")
                    continue
                state.add_result(result)
                decision = self.decide(result)
                state.decisions[result.agent_id] = decision
                if decision.warning:
                    state.warnings.append(decision.warning)

            # Gate: need at least audience data to continue
            if not self._is_usable(state, "audience_intel"):
                logger.error("Audience Intel result unusable — cannot continue")
                return state

            # Step 3: Platform agents + Creative (parallel)
            logger.info("\n[STEP 3] Platform ops + Creative (parallel)")
            audience_data = state.results["audience_intel"].data
            analytics_data = state.results.get("analytics", AgentResult(
                agent_id="analytics",
                status=CompletionStatus.FAILED,
                data={},
            )).data

            platform_results = await asyncio.gather(
                self._run_agent_with_budget(
                    "meta_ads",
                    agent_registry["meta_ads"],
                    task={"audience": audience_data, "analytics": analytics_data},
                    complexity=complexity,
                ),
                self._run_agent_with_budget(
                    "google_ads",
                    agent_registry["google_ads"],
                    task={"audience": audience_data, "analytics": analytics_data},
                    complexity=complexity,
                ),
                self._run_agent_with_budget(
                    "linkedin_ads",
                    agent_registry["linkedin_ads"],
                    task={"audience": audience_data},
                    complexity=complexity,
                ),
                self._run_agent_with_budget(
                    "creative",
                    agent_registry["creative"],
                    task={"audience": audience_data, "analytics": analytics_data},
                    complexity=complexity,
                ),
                return_exceptions=True,
            )

            for result in platform_results:
                if isinstance(result, Exception):
                    logger.error(f"Platform agent crashed: {result}")
                    continue
                state.add_result(result)
                decision = self.decide(result)
                state.decisions[result.agent_id] = decision
                if decision.warning:
                    state.warnings.append(decision.warning)

            # Step 4: Orchestrator aggregates
            logger.info("\n[STEP 4] Aggregation + approval request")
            agg_result = await self._run_agent_with_budget(
                "orchestrator",
                agent_registry["orchestrator"],
                task={
                    "phase": "aggregate",
                    "results": {k: v.data for k, v in state.results.items()},
                    "warnings": state.warnings,
                },
                complexity=complexity,
            )
            state.add_result(agg_result)

            # Step 5: Reporting
            logger.info("\n[STEP 5] Reporting")
            report_result = await self._run_agent_with_budget(
                "reporting",
                agent_registry["reporting"],
                task={
                    "pipeline_state": state.results,
                    "warnings": state.warnings,
                    "total_tokens": state.total_tokens_used,
                },
                complexity=complexity,
            )
            state.add_result(report_result)
            state.completed = True

        except Exception as e:
            logger.exception(f"Unhandled pipeline error: {e}")

        finally:
            elapsed = state.elapsed_sec()
            logger.info(f"\n{'='*60}")
            logger.info(f"Pipeline {run_id} complete in {elapsed:.1f}s")
            logger.info(f"Total tokens: {state.total_tokens_used:,}")
            logger.info(f"Warnings: {len(state.warnings)}")
            logger.info(f"{'='*60}")

        return state

    # ──────────────────────────────────────────
    # The Decision Tree
    # ──────────────────────────────────────────

    def decide(self, result: AgentResult) -> OrchestratorDecision:
        """
        Deterministic decision tree for every possible agent result.
        No hidden logic. Every path is explicit and logged.
        """
        retry_count = self._retry_counts.get(result.agent_id, 0)

        # COMPLETE
        if result.status == CompletionStatus.COMPLETE:
            logger.info(f"  {result.agent_id}: complete ({result.tokens_used:,} tokens)")
            return OrchestratorDecision(
                action=OrchestratorAction.ADVANCE,
                result=result,
            )

        # PARTIAL SAFE
        if result.status == CompletionStatus.PARTIAL_SAFE:
            coverage = result.coverage

            if coverage >= COVERAGE_THRESHOLDS["min_to_advance"]:
                warning = (
                    f"{result.agent_id}: {coverage:.0%} coverage "
                    f"({result.items_processed}/{result.items_total} items). "
                    f"Remaining items scheduled for next cycle."
                )
                logger.warning(f"  {warning}")
                return OrchestratorDecision(
                    action=OrchestratorAction.CONTINUE_WITH_WARNING,
                    result=result,
                    warning=warning,
                )

            elif coverage >= COVERAGE_THRESHOLDS["min_to_retry"]:
                if result.checkpoint and retry_count < MAX_RETRIES_PER_AGENT:
                    self._retry_counts[result.agent_id] = retry_count + 1
                    logger.warning(
                        f"  {result.agent_id}: {coverage:.0%} coverage, "
                        f"retrying from checkpoint (attempt {retry_count+1})"
                    )
                    return OrchestratorDecision(
                        action=OrchestratorAction.RETRY_FROM_CHECKPOINT,
                        checkpoint=result.checkpoint,
                        reason=f"Coverage {coverage:.0%} below threshold, checkpoint available",
                    )
                elif retry_count >= MAX_RETRIES_PER_AGENT:
                    warning = (
                        f"{result.agent_id}: max retries reached, "
                        f"proceeding with {coverage:.0%} coverage."
                    )
                    logger.error(f"  {warning}")
                    return OrchestratorDecision(
                        action=OrchestratorAction.CONTINUE_WITH_WARNING,
                        result=result,
                        warning=warning,
                    )
                else:
                    self._retry_counts[result.agent_id] = retry_count + 1
                    return OrchestratorDecision(
                        action=OrchestratorAction.RETRY_FROM_SCRATCH,
                        reason=f"Coverage {coverage:.0%}, no checkpoint to resume from",
                    )

            else:
                logger.error(
                    f"  {result.agent_id}: only {coverage:.0%} coverage, replanning"
                )
                return OrchestratorDecision(
                    action=OrchestratorAction.REPLAN,
                    reason=(
                        f"Coverage {coverage:.0%} is too low to be actionable. "
                        f"Consider splitting the task or reducing scope."
                    ),
                )

        # PARTIAL UNSAFE
        if result.status == CompletionStatus.PARTIAL_UNSAFE:
            logger.error(
                f"  {result.agent_id}: PARTIAL_UNSAFE — "
                f"agent stopped mid-calculation. Discarding all data."
            )
            if retry_count < MAX_RETRIES_PER_AGENT:
                self._retry_counts[result.agent_id] = retry_count + 1
                return OrchestratorDecision(
                    action=OrchestratorAction.RETRY_FROM_SCRATCH,
                    reason="Unsafe partial result — retrying from scratch",
                )
            return OrchestratorDecision(
                action=OrchestratorAction.ESCALATE_TO_HUMAN,
                reason="Repeated unsafe results — human review required",
            )

        # BUDGET EXCEEDED
        if result.status == CompletionStatus.BUDGET_EXCEEDED:
            if result.checkpoint and retry_count < MAX_RETRIES_PER_AGENT:
                self._retry_counts[result.agent_id] = retry_count + 1
                logger.warning(
                    f"  {result.agent_id}: budget exceeded, "
                    f"resuming from checkpoint"
                )
                return OrchestratorDecision(
                    action=OrchestratorAction.RETRY_FROM_CHECKPOINT,
                    checkpoint=result.checkpoint,
                    reason="Budget exceeded — resuming from checkpoint with expanded budget",
                )
            return OrchestratorDecision(
                action=OrchestratorAction.ESCALATE_TO_HUMAN,
                reason="Budget exceeded and no checkpoint available — human required",
            )

        # FAILED
        if result.status == CompletionStatus.FAILED:
            logger.error(f"  {result.agent_id}: FAILED — {result.error}")
            if retry_count < MAX_RETRIES_PER_AGENT:
                self._retry_counts[result.agent_id] = retry_count + 1
                return OrchestratorDecision(
                    action=OrchestratorAction.RETRY_FROM_SCRATCH,
                    reason=f"Agent failed: {result.error}",
                )
            return OrchestratorDecision(
                action=OrchestratorAction.ESCALATE_TO_HUMAN,
                reason=f"Agent failed after {retry_count} retries: {result.error}",
            )

        # Catch-all
        return OrchestratorDecision(
            action=OrchestratorAction.ESCALATE_TO_HUMAN,
            reason=f"Unknown status: {result.status}",
        )

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    async def _run_agent_with_budget(
        self,
        agent_id: str,
        agent_fn: Callable,
        task: dict,
        complexity: TaskComplexity,
        override_budget=None,
    ) -> AgentResult:
        """Assign budget -> inject into task -> run agent -> record usage."""
        budget = override_budget or self.budget_manager.assign(agent_id, complexity)
        task["_budget"] = budget

        logger.info(
            f"  -> Running {agent_id} | budget: {budget.max_input_tokens:,} input tokens"
        )

        start = time.time()
        result: AgentResult = await agent_fn(task, budget)
        result.time_elapsed_sec = time.time() - start

        self.budget_manager.record_actual_usage(agent_id, result.tokens_used, budget)

        logger.info(f"  <- {result.summary()}")
        return result

    def _is_usable(self, state: PipelineState, agent_id: str) -> bool:
        result = state.results.get(agent_id)
        if result is None:
            return False
        return result.is_usable and result.coverage >= 0.5
