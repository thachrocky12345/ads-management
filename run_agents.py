"""
run_agents.py
─────────────
Live integration runner for the rebuilt agents.
Runs both agents with real Claude API calls.

Usage:
    # Requires ANTHROPIC_API_KEY in .env or environment
    python run_agents.py

    # Test only Analytics agent
    python run_agents.py --agent analytics

    # Test only Audience Intel agent
    python run_agents.py --agent audience

    # Simulate tight budget to test partial_safe handling
    python run_agents.py --tight-budget
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

sys.path.insert(0, ".")

from core.types import TokenBudget
from core.budget_manager import TokenBudgetManager
from core.orchestrator import Orchestrator, OrchestratorAction
from agents.audience_intel_agent import AudienceIntelAgent, AudienceIntelResult, ScoredSegment
from agents.analytics_agent import AnalyticsAgent, AnalyticsResult

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DIV  = "─" * 70
DIV2 = "═" * 70


def run_audience_intel(tight_budget: bool = False) -> None:
    print(f"\n{DIV2}")
    print("  AUDIENCE INTEL AGENT  [HubSpot + GA4 + Claude Sonnet 4.5]")
    print(DIV2)

    budget_manager = TokenBudgetManager()
    orchestrator   = Orchestrator(budget_manager)
    agent          = AudienceIntelAgent()

    if tight_budget:
        budget = TokenBudget(
            input_tokens=8_000,
            output_tokens=2_000,
            max_turns=3,
            safety_margin=400,
        )
        print("  ⚡ TIGHT budget mode — will trigger partial_safe + retry demo")
    else:
        budget = budget_manager.assign("audience_intel", complexity="normal")

    print(f"  Budget: {budget.effective_input_limit:,} input / "
          f"{budget.output_tokens:,} output tokens\n")

    result   = agent.run(task_id="live_run_001", budget=budget)
    decision = orchestrator.evaluate(result)

    print(f"\n{DIV}")
    print(f"  STATUS:   {result.status.value.upper()}")
    print(f"  COVERAGE: {result.coverage:.0%} "
          f"({result.items_processed}/{result.items_total} segments)")
    print(f"  TOKENS:   {result.tokens_used:,}")
    print(f"  DECISION: {decision.action.value.upper()}")
    print(DIV)

    # ── Print scored segments ─────────────────────────────────────────
    if result.is_usable and result.data:
        data = result.data
        segments = (
            data.scored_segments if isinstance(data, AudienceIntelResult)
            else data  # fallback if partial list returned
        )

        if segments:
            print(f"\n  SCORED SEGMENTS:")
            print(f"  {'Segment':<38} {'ROAS':>5} {'LTV':>4} {'Priority':<8} {'Budget Rec'}")
            print(f"  {'-'*72}")
            for s in segments:
                name = s.segment_name if isinstance(s, ScoredSegment) else str(s)
                if isinstance(s, ScoredSegment):
                    print(
                        f"  {s.segment_name:<38} "
                        f"{s.roas_prediction:>4.1f}x "
                        f"{s.ltv_score:>4.1f} "
                        f"{s.priority:<8} "
                        f"{s.budget_rec}"
                    )
                    print(f"    → {s.targeting_notes[:90]}...")
                    if s.ad_copy_angles:
                        print(f"    Copy angles: {' | '.join(s.ad_copy_angles[:2])}")
                    print()

        if isinstance(data, AudienceIntelResult) and data.targeting_strategy:
            print(f"  STRATEGY:")
            print(f"  {data.targeting_strategy}")
            print(f"\n  Top segment:     {data.top_segment_id}")
            print(f"  Lookalike seeds: {data.lookalike_seed_ids}")
            print(f"  Total scale audience: {data.total_addressable:,} contacts")

    # ── Handle retry if needed ────────────────────────────────────────
    if decision.action == OrchestratorAction.RETRY_FROM_CHECKPOINT:
        print(f"\n  🔁 RETRYING from checkpoint with expanded budget...")
        retry_result = agent.run(
            task_id="live_run_001_retry",
            budget=decision.new_budget,
            resume_from=decision.checkpoint,
        )
        retry_decision = orchestrator.evaluate(retry_result)
        print(f"  Retry: {retry_result.status.value} | "
              f"coverage={retry_result.coverage:.0%} | "
              f"decision={retry_decision.action.value}")

    if decision.warning:
        print(f"\n  ⚠  {decision.warning}")


def run_analytics(tight_budget: bool = False) -> None:
    print(f"\n{DIV2}")
    print("  ANALYTICS AGENT  [GA4 + Claude Sonnet 4.5 ROAS Join]")
    print(DIV2)

    budget_manager = TokenBudgetManager()
    orchestrator   = Orchestrator(budget_manager)
    agent          = AnalyticsAgent()

    if tight_budget:
        # Budget that triggers partial_unsafe (enough for T1+T2, not T3)
        budget = TokenBudget(
            input_tokens=4_000,
            output_tokens=1_000,
            max_turns=2,
            safety_margin=200,
        )
        print("  ⚡ TIGHT budget — will trigger partial_unsafe demo")
    else:
        budget = budget_manager.assign("analytics", complexity="normal")

    print(f"  Budget: {budget.effective_input_limit:,} input tokens\n")

    result   = agent.run(task_id="live_run_001", budget=budget)
    decision = orchestrator.evaluate(result)

    print(f"\n{DIV}")
    print(f"  STATUS:   {result.status.value.upper()}")
    print(f"  TOKENS:   {result.tokens_used:,}")
    print(f"  DECISION: {decision.action.value.upper()}")
    if result.error:
        print(f"  REASON:   {result.error}")
    print(DIV)

    if result.is_usable and result.data and isinstance(result.data, AnalyticsResult):
        d = result.data
        print(f"\n  ROAS BY SEGMENT:")
        print(f"  {'Segment':<32} {'Platform':<10} {'Spend':>8} {'Revenue':>9} "
              f"{'ROAS':>6}  {'Verdict':<8} Action")
        print(f"  {'-'*90}")
        for r in sorted(d.roas_records, key=lambda x: x.roas, reverse=True):
            verdict_icon = {
                "scale": "✅", "hold": "⚠️ ",
                "cut": "❌", "pause": "⏸ ",
            }.get(r.verdict, "  ")
            print(
                f"  {r.segment_name:<32} {r.platform:<10} "
                f"${r.spend_usd:>7.0f} ${r.revenue_usd:>8.0f} "
                f"{r.roas:>5.1f}x  {verdict_icon}{r.verdict:<6} {r.action}"
            )

        print(f"\n  SUMMARY:")
        print(f"  Total spend:   ${d.total_spend_usd:,.0f}")
        print(f"  Total revenue: ${d.total_revenue_usd:,.0f}")
        print(f"  Blended ROAS:  {d.blended_roas:.2f}x")
        print(f"  Top performer: {d.top_performer}")
        print(f"  Worst:         {d.worst_performer}")

        if d.anomalies:
            print(f"\n  ANOMALIES:")
            for a in d.anomalies:
                print(f"  ⚠  {a}")

        print(f"\n  ANALYST SUMMARY:")
        print(f"  {d.analyst_summary}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run rebuilt ads agents")
    parser.add_argument(
        "--agent",
        choices=["analytics", "audience", "both"],
        default="both",
    )
    parser.add_argument(
        "--tight-budget",
        action="store_true",
        help="Use tight budget to demo partial_safe / partial_unsafe handling",
    )
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n❌  ANTHROPIC_API_KEY not set.")
        print("    Copy .env.example → .env and add your key, then re-run.\n")
        sys.exit(1)

    if args.agent in ("audience", "both"):
        run_audience_intel(tight_budget=args.tight_budget)

    if args.agent in ("analytics", "both"):
        run_analytics(tight_budget=args.tight_budget)
