"""
core/models.py
──────────────
All shared types for the ads agent network.
Every agent returns an AgentResult. Every budget is a TokenBudget.
No circular imports — this is the leaf dependency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class CompletionStatus(Enum):
    COMPLETE = "complete"
    PARTIAL_SAFE = "partial_safe"
    PARTIAL_UNSAFE = "partial_unsafe"
    BUDGET_EXCEEDED = "budget_exceeded"
    FAILED = "failed"


class TaskComplexity(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class OrchestratorAction(Enum):
    ADVANCE = "advance"
    CONTINUE_WITH_WARNING = "continue_with_warning"
    RETRY_FROM_CHECKPOINT = "retry_from_checkpoint"
    RETRY_FROM_SCRATCH = "retry_from_scratch"
    REPLAN = "replan"
    ESCALATE_TO_HUMAN = "escalate_to_human"


# ─────────────────────────────────────────────
# TokenBudget
# ─────────────────────────────────────────────

@dataclass
class TokenBudget:
    """
    A token budget assigned to an agent BEFORE it starts work.
    The agent checks this before each unit of work.
    """
    agent_id: str
    max_input_tokens: int
    max_output_tokens: int
    max_turns: int
    safety_margin_pct: float = 0.15

    @property
    def total_budget(self) -> int:
        return self.max_input_tokens + self.max_output_tokens

    @property
    def safety_threshold(self) -> int:
        return int(self.max_input_tokens * self.safety_margin_pct)

    def is_safe_to_start_unit(self, tokens_used: int, estimated_unit_cost: int) -> bool:
        """Check if there's enough budget to complete one more work unit."""
        remaining = self.max_input_tokens - tokens_used
        return remaining >= (estimated_unit_cost + self.safety_threshold)

    def to_prompt_block(self) -> str:
        """Inject budget constraints into an agent's system prompt."""
        return (
            f"TOKEN BUDGET FOR THIS TASK:\n"
            f"  Input:  {self.max_input_tokens:,} tokens\n"
            f"  Output: {self.max_output_tokens:,} tokens\n"
            f"  Turns:  {self.max_turns} maximum\n"
            f"  Safety margin: {self.safety_margin_pct:.0%}\n\n"
            f"RULES:\n"
            f"1. Before starting each work unit, check if you have enough budget.\n"
            f"2. If not, STOP and return what you have with status partial_safe.\n"
            f"3. Never start a unit you cannot finish.\n"
        )

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_turns": self.max_turns,
            "safety_margin_pct": self.safety_margin_pct,
            "total_budget": self.total_budget,
            "safety_threshold": self.safety_threshold,
        }


# ─────────────────────────────────────────────
# AgentResult
# ─────────────────────────────────────────────

@dataclass
class AgentResult:
    """
    The envelope every agent returns. Status is explicit —
    no silent partial returns.
    """
    agent_id: str
    status: CompletionStatus
    data: Any = field(default_factory=dict)
    items_processed: int = 0
    items_total: int = 0
    tokens_used: int = 0
    checkpoint: Optional[dict] = None
    error: Optional[str] = None
    warning: Optional[str] = None
    time_elapsed_sec: float = 0.0

    @property
    def coverage(self) -> float:
        if self.items_total <= 0:
            return 1.0 if self.status == CompletionStatus.COMPLETE else 0.0
        return self.items_processed / self.items_total

    @property
    def is_usable(self) -> bool:
        return self.status in (CompletionStatus.COMPLETE, CompletionStatus.PARTIAL_SAFE)

    def summary(self) -> str:
        cov = f"{self.coverage:.0%}" if self.items_total > 0 else "N/A"
        return (
            f"{self.agent_id}: {self.status.value} | "
            f"coverage={cov} | tokens={self.tokens_used:,} | "
            f"{self.time_elapsed_sec:.1f}s"
        )

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "data": self.data,
            "items_processed": self.items_processed,
            "items_total": self.items_total,
            "tokens_used": self.tokens_used,
            "coverage": self.coverage,
            "is_usable": self.is_usable,
            "error": self.error,
            "warning": self.warning,
            "time_elapsed_sec": self.time_elapsed_sec,
        }


# ─────────────────────────────────────────────
# OrchestratorDecision
# ─────────────────────────────────────────────

@dataclass
class OrchestratorDecision:
    """What the Orchestrator decides to do with an agent result."""
    action: OrchestratorAction
    result: Optional[AgentResult] = None
    checkpoint: Optional[dict] = None
    warning: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "warning": self.warning,
            "reason": self.reason,
        }


# ─────────────────────────────────────────────
# PipelineState
# ─────────────────────────────────────────────

@dataclass
class PipelineState:
    """Tracks the full state of a pipeline run."""
    run_id: str = ""
    results: dict[str, AgentResult] = field(default_factory=dict)
    decisions: dict[str, OrchestratorDecision] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    completed: bool = False
    _start_time: float = field(default_factory=time.time)

    @property
    def total_tokens_used(self) -> int:
        return sum(r.tokens_used for r in self.results.values())

    def add_result(self, result: AgentResult) -> None:
        self.results[result.agent_id] = result

    def elapsed_sec(self) -> float:
        return time.time() - self._start_time

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "completed": self.completed,
            "elapsed_sec": round(self.elapsed_sec(), 1),
            "total_tokens_used": self.total_tokens_used,
            "warnings": self.warnings,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "decisions": {k: v.to_dict() for k, v in self.decisions.items()},
        }
