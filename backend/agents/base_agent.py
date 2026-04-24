"""
agents/base_agent.py
────────────────────
Base class for all specialist agents.
Provides budget checking and checkpoint discipline.
"""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod

from core.models import AgentResult, CompletionStatus, TokenBudget


class BaseAgent(ABC):
    """
    All agents extend this. The key discipline is check_budget():
    call it BEFORE each work unit, never during.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._tokens_used = 0

    def check_budget(self, budget: TokenBudget, estimated_unit_cost: int = 4000) -> bool:
        """
        Check if there's enough budget for one more work unit.
        Returns False when the agent should stop cleanly.
        """
        return budget.is_safe_to_start_unit(self._tokens_used, estimated_unit_cost)

    def consume_tokens(self, count: int) -> None:
        """Record token consumption for a completed work unit."""
        self._tokens_used += count

    def simulate_token_usage(self, base: int = 3000, variance: int = 1500) -> int:
        """Simulate realistic token usage for a work unit."""
        usage = base + random.randint(-variance, variance)
        self.consume_tokens(usage)
        return usage

    async def simulate_latency(self, base_ms: int = 200, variance_ms: int = 100) -> None:
        """Simulate realistic API latency."""
        delay = (base_ms + random.randint(-variance_ms, variance_ms)) / 1000
        await asyncio.sleep(max(0.05, delay))

    def make_result(
        self,
        status: CompletionStatus,
        data: dict,
        items_processed: int = 0,
        items_total: int = 0,
        checkpoint: dict | None = None,
        error: str | None = None,
    ) -> AgentResult:
        """Build an AgentResult with current token usage."""
        return AgentResult(
            agent_id=self.agent_id,
            status=status,
            data=data,
            items_processed=items_processed,
            items_total=items_total,
            tokens_used=self._tokens_used,
            checkpoint=checkpoint,
            error=error,
        )

    @abstractmethod
    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        """Execute the agent's task within its budget."""
        ...
