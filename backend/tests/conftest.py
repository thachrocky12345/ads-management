"""
tests/conftest.py
─────────────────
Shared fixtures for all tests.
"""

import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from core.models import AgentResult, CompletionStatus
from core.budget_manager import TokenBudgetManager
from core.orchestrator import Orchestrator


@pytest.fixture
def budget_manager():
    return TokenBudgetManager(safety_margin_pct=0.15)


@pytest.fixture
def orchestrator(budget_manager):
    return Orchestrator(budget_manager)


def make_result(
    status,
    processed=5,
    total=5,
    checkpoint=None,
    error=None,
    agent_id="audience_intel",
):
    return AgentResult(
        agent_id=agent_id,
        status=status,
        data={"segments": [{"segment_id": f"seg_{i}"} for i in range(processed)]},
        items_processed=processed,
        items_total=total,
        tokens_used=15_000,
        checkpoint=checkpoint,
        error=error,
    )
