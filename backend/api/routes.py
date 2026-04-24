"""
api/routes.py
─────────────
FastAPI routes for the ads agent network.
Connects the frontend dashboard to the Orchestrator pipeline.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.models import TaskComplexity, PipelineState
from core.budget_manager import TokenBudgetManager, get_agent_configs
from core.orchestrator import Orchestrator
from agents.registry import build_agent_registry

router = APIRouter(prefix="/api")

# Shared state
_budget_manager = TokenBudgetManager(safety_margin_pct=0.15)
_orchestrator = Orchestrator(_budget_manager)
_pipeline_runs: dict[str, PipelineState] = {}
_running_tasks: dict[str, asyncio.Task] = {}


# ─────────────────────────────────────────────
# Request/Response models
# ─────────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    goal: str = "Analyze last 7 days ROAS by segment, update audience targeting, adjust bids on all platforms."
    complexity: str = "normal"


class DryRunRequest(BaseModel):
    complexity: str = "normal"


def _parse_complexity(value: str) -> TaskComplexity:
    mapping = {"low": TaskComplexity.LOW, "normal": TaskComplexity.NORMAL, "high": TaskComplexity.HIGH}
    if value not in mapping:
        raise HTTPException(status_code=400, detail=f"Invalid complexity: {value}. Use low/normal/high.")
    return mapping[value]


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok", "service": "ads-agent-network"}


@router.get("/agents")
async def list_agents():
    """List all agents with their models, budgets, and pricing."""
    return {"agents": get_agent_configs()}


@router.post("/pipeline/run")
async def run_pipeline(req: PipelineRunRequest):
    """Start a full pipeline run. Returns immediately with run_id."""
    complexity = _parse_complexity(req.complexity)
    registry = build_agent_registry()

    # Create a fresh orchestrator for each run to reset retry counts
    orchestrator = Orchestrator(_budget_manager)

    # Start pipeline in background
    async def _run():
        state = await orchestrator.run_pipeline(
            goal=req.goal,
            agent_registry=registry,
            complexity=complexity,
        )
        _pipeline_runs[state.run_id] = state
        return state

    task = asyncio.create_task(_run())

    # Wait briefly for the pipeline to initialize and get run_id
    await asyncio.sleep(0.1)

    # Find the run_id from the task if it completed quickly
    if task.done():
        state = task.result()
        return state.to_dict()

    # For longer runs, we need to track the task
    # The pipeline creates its own run_id internally, so we run synchronously
    # to ensure we can return the state
    state = await task
    return state.to_dict()


@router.post("/pipeline/dry-run")
async def dry_run_pipeline(req: DryRunRequest):
    """Estimate cost without running the pipeline."""
    complexity = _parse_complexity(req.complexity)
    estimate = _budget_manager.estimate_pipeline_cost(complexity)
    return estimate


@router.get("/pipeline/status/{run_id}")
async def get_pipeline_status(run_id: str):
    """Get the status of a pipeline run."""
    state = _pipeline_runs.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found")
    return state.to_dict()
