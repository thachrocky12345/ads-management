"""
core/budget_manager.py
──────────────────────
Assigns token budgets to agents BEFORE they start work.
Budgets are based on historical averages, scaled by task complexity.
The Orchestrator calls this — agents never self-assign budgets.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import logging

from .models import TokenBudget, TaskComplexity

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Historical baseline budgets per agent
# (tuned from actual runs — update these over time)
# ─────────────────────────────────────────────

_BASE_BUDGETS: dict[str, dict] = {
    "orchestrator": {
        "input":  12_800,
        "output":  3_200,
        "turns":       4,
        "note": "Goal decomposition + aggregation",
    },
    "audience_intel": {
        "input":  25_000,
        "output":  7_000,
        "turns":       5,
        "note": "CRM ingest + segment scoring + lookalike gen",
    },
    "analytics": {
        "input":  18_000,
        "output":  3_500,
        "turns":       3,
        "note": "Spend pull + revenue join + ROAS calculation",
    },
    "meta_ads": {
        "input":  12_000,
        "output":  2_200,
        "turns":       3,
        "note": "Bid adjustment + audience upload",
    },
    "google_ads": {
        "input":  11_000,
        "output":  2_200,
        "turns":       3,
        "note": "Keyword bids + negative keywords",
    },
    "linkedin_ads": {
        "input":   7_000,
        "output":  1_400,
        "turns":       2,
        "note": "Job title targeting + lead gen forms",
    },
    "creative": {
        "input":  14_000,
        "output":  5_600,
        "turns":       4,
        "note": "Multimodal ad analysis + copy generation",
    },
    "reporting": {
        "input":   8_400,
        "output":  2_400,
        "turns":       2,
        "note": "Compress results + generate digest",
    },
}

# Complexity multipliers — scale budget up or down
_COMPLEXITY_MULTIPLIERS: dict[TaskComplexity, float] = {
    TaskComplexity.LOW:    0.65,   # Small SMB, few campaigns
    TaskComplexity.NORMAL: 1.00,   # Standard weekly analysis
    TaskComplexity.HIGH:   1.45,   # Large CRM, many ad sets, full audit
}

# Per-model pricing (USD per 1M tokens, March 2026)
MODEL_PRICING: dict[str, dict] = {
    "claude-sonnet-4-5":  {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5":   {"input": 0.80,  "output":  4.00},
    "gpt-5":              {"input": 15.00, "output": 60.00},
    "gemini-3-pro":       {"input": 7.00,  "output": 21.00},
}

# Which model each agent uses
AGENT_MODELS: dict[str, str] = {
    "orchestrator":   "claude-sonnet-4-5",
    "audience_intel": "claude-sonnet-4-5",
    "analytics":      "gpt-5",
    "meta_ads":       "gpt-5",
    "google_ads":     "gpt-5",
    "linkedin_ads":   "gpt-5",
    "creative":       "gemini-3-pro",
    "reporting":      "claude-haiku-4-5",
}


class TokenBudgetManager:
    """
    Assigns token budgets to agents before they start.
    Tracks spend across the pipeline and learns from history.
    """

    def __init__(
        self,
        safety_margin_pct: float = 0.15,
        max_retries_per_agent: int = 2,
    ):
        self.safety_margin_pct = safety_margin_pct
        self.max_retries = max_retries_per_agent
        self._usage_history: list[dict] = []   # For future auto-tuning

    # ──────────────────────────────────────────
    # Primary API — called by Orchestrator
    # ──────────────────────────────────────────

    def assign(
        self,
        agent_id: str,
        complexity: TaskComplexity = TaskComplexity.NORMAL,
        override_input: Optional[int] = None,
        override_output: Optional[int] = None,
    ) -> TokenBudget:
        """
        Assign a token budget to an agent.
        Called BEFORE the agent starts — never mid-run.
        """
        if agent_id not in _BASE_BUDGETS:
            raise ValueError(
                f"Unknown agent '{agent_id}'. "
                f"Valid agents: {list(_BASE_BUDGETS.keys())}"
            )

        base = _BASE_BUDGETS[agent_id]
        multiplier = _COMPLEXITY_MULTIPLIERS[complexity]

        budget = TokenBudget(
            agent_id=agent_id,
            max_input_tokens=override_input or int(base["input"] * multiplier),
            max_output_tokens=override_output or int(base["output"] * multiplier),
            max_turns=base["turns"],
            safety_margin_pct=self.safety_margin_pct,
        )

        logger.info(
            f"Budget assigned → {agent_id} | "
            f"input={budget.max_input_tokens:,} "
            f"output={budget.max_output_tokens:,} "
            f"turns={budget.max_turns} "
            f"[{complexity.value} complexity]"
        )
        return budget

    def assign_retry_budget(
        self,
        original_budget: TokenBudget,
        retry_number: int,
        from_checkpoint: bool = False,
    ) -> TokenBudget:
        """
        Grant expanded budget for a retry.
        Each retry gets progressively more — but capped.
        Checkpoint retries get less (they start partway through).
        """
        if retry_number > self.max_retries:
            raise RuntimeError(
                f"Agent {original_budget.agent_id} has exceeded max retries "
                f"({self.max_retries}). Escalating to human."
            )

        # Checkpoint retries: 40% more (less work remaining)
        # Full retries: 60% more (need to redo everything)
        expansion = 1.40 if from_checkpoint else 1.60
        multiplier = expansion ** retry_number

        new_budget = TokenBudget(
            agent_id=original_budget.agent_id,
            max_input_tokens=int(original_budget.max_input_tokens * multiplier),
            max_output_tokens=int(original_budget.max_output_tokens * multiplier),
            max_turns=original_budget.max_turns + retry_number,
            safety_margin_pct=original_budget.safety_margin_pct,
        )

        logger.warning(
            f"Retry budget #{retry_number} → {original_budget.agent_id} | "
            f"input={new_budget.max_input_tokens:,} "
            f"(+{(multiplier-1)*100:.0f}%)"
        )
        return new_budget

    # ──────────────────────────────────────────
    # Cost estimation
    # ──────────────────────────────────────────

    def estimate_cost(self, budget: TokenBudget) -> float:
        """Estimate max cost for a budget in USD."""
        model = AGENT_MODELS.get(budget.agent_id, "claude-sonnet-4-5")
        pricing = MODEL_PRICING[model]
        cost = (
            (budget.max_input_tokens / 1_000_000) * pricing["input"] +
            (budget.max_output_tokens / 1_000_000) * pricing["output"]
        )
        return round(cost, 6)

    def estimate_pipeline_cost(
        self,
        complexity: TaskComplexity = TaskComplexity.NORMAL
    ) -> dict:
        """Estimate cost for a full analysis run."""
        total = 0.0
        breakdown = {}
        for agent_id in _BASE_BUDGETS:
            budget = self.assign(agent_id, complexity)
            cost = self.estimate_cost(budget)
            breakdown[agent_id] = {
                "model": AGENT_MODELS.get(agent_id),
                "tokens": budget.total_budget,
                "cost_usd": cost,
            }
            total += cost
        return {"total_usd": round(total, 4), "per_agent": breakdown}

    def record_actual_usage(self, agent_id: str, tokens_used: int, budget: TokenBudget):
        """Track real usage for future budget auto-tuning."""
        utilization = tokens_used / budget.total_budget
        self._usage_history.append({
            "agent_id": agent_id,
            "tokens_used": tokens_used,
            "budget": budget.total_budget,
            "utilization": utilization,
        })
        if utilization > 0.90:
            logger.warning(
                f"High utilization alert: {agent_id} used "
                f"{utilization:.0%} of budget. Consider increasing base."
            )
