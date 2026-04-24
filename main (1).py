"""
main.py
────────
Run the full Ads Agent Network pipeline.

Usage:
    python main.py                    # Normal complexity
    python main.py --complexity high  # High complexity (more tokens)
    python main.py --dry-run          # Just estimate cost, don't run
"""

import asyncio
import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from core.models import TaskComplexity
from core.budget_manager import TokenBudgetManager
from core.orchestrator import Orchestrator
from agents.specialist_agents import build_agent_registry


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


async def main(complexity: TaskComplexity, dry_run: bool = False):

    budget_manager = TokenBudgetManager(safety_margin_pct=0.15)

    # ── Dry run: show cost estimate only ──────────────────────────
    if dry_run:
        estimate = budget_manager.estimate_pipeline_cost(complexity)
        print(f"\n{'='*55}")
        print(f"  COST ESTIMATE — {complexity.value.upper()} complexity")
        print(f"{'='*55}")
        print(f"  {'Agent':<18} {'Model':<22} {'Tokens':>8}  {'Cost':>10}")
        print(f"  {'-'*53}")
        for agent, info in estimate["per_agent"].items():
            print(
                f"  {agent:<18} {info['model']:<22} "
                f"{info['tokens']:>8,}  ${info['cost_usd']:>9.5f}"
            )
        print(f"  {'-'*53}")
        print(f"  {'TOTAL':<42} ${estimate['total_usd']:>9.4f}")
        print(f"\n  Monthly (1x/day):   ${estimate['total_usd'] * 30:.2f}")
        print(f"  Monthly (3x/day):   ${estimate['total_usd'] * 90:.2f}")
        print(f"  Monthly (hourly):   ${estimate['total_usd'] * 720:.2f}")
        print(f"{'='*55}\n")
        return

    # ── Full pipeline run ─────────────────────────────────────────
    orchestrator = Orchestrator(budget_manager)
    registry = build_agent_registry()

    state = await orchestrator.run_pipeline(
        goal="Analyze last 7 days ROAS by segment, update audience targeting, "
             "adjust bids on all platforms, generate new creative for top segments.",
        agent_registry=registry,
        complexity=complexity,
    )

    # ── Print results ─────────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  PIPELINE RESULTS — Run {state.run_id}")
    print(f"{'='*55}")
    print(f"  Completed:     {state.completed}")
    print(f"  Elapsed:       {state.elapsed_sec():.1f}s")
    print(f"  Total tokens:  {state.total_tokens_used:,}")
    print(f"  Warnings:      {len(state.warnings)}")

    print(f"\n  {'Agent':<18} {'Status':<18} {'Coverage':>10}  {'Tokens':>8}")
    print(f"  {'-'*56}")
    for agent_id, result in state.results.items():
        print(
            f"  {agent_id:<18} {result.status.value:<18} "
            f"{result.coverage:>9.0%}  {result.tokens_used:>8,}"
        )

    if state.warnings:
        print(f"\n  WARNINGS:")
        for w in state.warnings:
            print(f"    ⚠  {w}")

    # Show final digest if available
    if "reporting" in state.results:
        digest = state.results["reporting"].data.get("digest", {})
        if digest:
            print(f"\n  DIGEST: {digest.get('top_insight', 'N/A')}")
            print(f"  Next run: {digest.get('next_run', 'N/A')}")

    print(f"{'='*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Ads Agent Network")
    parser.add_argument(
        "--complexity",
        choices=["low", "normal", "high"],
        default="normal",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    complexity_map = {
        "low": TaskComplexity.LOW,
        "normal": TaskComplexity.NORMAL,
        "high": TaskComplexity.HIGH,
    }

    asyncio.run(main(
        complexity=complexity_map[args.complexity],
        dry_run=args.dry_run,
    ))
