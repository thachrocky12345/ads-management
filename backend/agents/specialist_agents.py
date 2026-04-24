"""
agents/specialist_agents.py
────────────────────────────
All 8 specialist agents for the ads network.
Each returns structured data with explicit CompletionStatus.

These are simulation agents — replace the _simulate_* methods
with real LLM + API calls for production use.
"""

from __future__ import annotations

import random

from core.models import AgentResult, CompletionStatus, TokenBudget
from .base_agent import BaseAgent


# ─────────────────────────────────────────────
# Orchestrator Agent (Claude Sonnet 4.5)
# ─────────────────────────────────────────────

class OrchestratorAgent(BaseAgent):
    """Decomposes goals into sub-tasks and aggregates results."""

    def __init__(self):
        super().__init__("orchestrator")

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        await self.simulate_latency(300)
        phase = task.get("phase", "decompose")

        if phase == "decompose":
            self.simulate_token_usage(4000, 1000)
            return self.make_result(
                status=CompletionStatus.COMPLETE,
                data={
                    "phase": "decompose",
                    "segments": [
                        "past_customers",
                        "women_35_44_local",
                        "lookalike_top_20pct",
                        "men_25_34_broad",
                        "cold_interest_home",
                    ],
                    "platforms": ["meta", "google", "linkedin"],
                    "date_range": "last_7_days",
                },
                items_processed=1,
                items_total=1,
            )
        else:
            # Aggregation phase
            self.simulate_token_usage(5000, 1500)
            results = task.get("results", {})
            warnings = task.get("warnings", [])
            return self.make_result(
                status=CompletionStatus.COMPLETE,
                data={
                    "phase": "aggregate",
                    "agents_completed": list(results.keys()),
                    "warning_count": len(warnings),
                    "approved_actions": [
                        "scale_past_customers",
                        "hold_lookalike",
                        "cut_men_25_34",
                        "pause_cold_interest",
                    ],
                },
                items_processed=1,
                items_total=1,
            )


# ─────────────────────────────────────────────
# Audience Intel Agent (Claude Sonnet 4.5)
# ─────────────────────────────────────────────

class AudienceIntelAgent(BaseAgent):
    """
    Scores audience segments from CRM + pixel data.
    Checkpoints at each segment boundary.
    """

    def __init__(self):
        super().__init__("audience_intel")

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        segments = task.get("segments", [
            "past_customers",
            "women_35_44_local",
            "lookalike_top_20pct",
            "men_25_34_broad",
            "cold_interest_home",
        ])
        total = len(segments)
        scored = []

        for i, segment_id in enumerate(segments):
            # Budget check BEFORE each segment — never mid-analysis
            if not self.check_budget(budget, estimated_unit_cost=4500):
                return self.make_result(
                    status=CompletionStatus.PARTIAL_SAFE,
                    data={"segments": scored},
                    items_processed=i,
                    items_total=total,
                    checkpoint={
                        "completed_segments": [s["segment_id"] for s in scored],
                        "remaining_segments": segments[i:],
                    },
                )

            await self.simulate_latency(250)
            self.simulate_token_usage(4200, 800)

            scored.append({
                "segment_id": segment_id,
                "score": round(random.uniform(0.3, 0.95), 2),
                "size": random.randint(500, 15000),
                "recommended_action": random.choice(["scale", "hold", "cut", "pause"]),
            })

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data={"segments": scored},
            items_processed=total,
            items_total=total,
        )


# ─────────────────────────────────────────────
# Analytics Agent (GPT-5)
# ─────────────────────────────────────────────

class AnalyticsAgent(BaseAgent):
    """
    Pulls spend + revenue, joins to calculate ROAS per segment.
    The ROAS join is atomic — if budget is too low to complete it,
    returns PARTIAL_UNSAFE (never half-calculated ROAS).
    """

    def __init__(self):
        super().__init__("analytics")

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        # Turn 1: Pull spend data
        await self.simulate_latency(300)
        self.simulate_token_usage(5000, 1000)

        spend_data = [
            {"segment": "past_customers",      "spend": 90.0,  "clicks": 120},
            {"segment": "women_35_44_local",    "spend": 180.0, "clicks": 340},
            {"segment": "lookalike_top_20pct",  "spend": 220.0, "clicks": 280},
            {"segment": "men_25_34_broad",      "spend": 310.0, "clicks": 190},
            {"segment": "cold_interest_home",   "spend": 150.0, "clicks": 85},
        ]

        # Turn 2: Pull revenue data
        if not self.check_budget(budget, estimated_unit_cost=5000):
            return self.make_result(
                status=CompletionStatus.PARTIAL_UNSAFE,
                data=None,
                error="Budget too low for ROAS join — cannot return half-calculated metrics",
            )

        await self.simulate_latency(300)
        self.simulate_token_usage(5000, 1000)

        revenue_data = {
            "past_customers":     810.0,
            "women_35_44_local":  960.0,
            "lookalike_top_20pct": 770.0,
            "men_25_34_broad":    620.0,
            "cold_interest_home": 180.0,
        }

        # Turn 3: Join and calculate ROAS (atomic)
        await self.simulate_latency(200)
        self.simulate_token_usage(3000, 500)

        roas_report = []
        for row in spend_data:
            seg = row["segment"]
            revenue = revenue_data.get(seg, 0)
            roas = round(revenue / row["spend"], 2) if row["spend"] > 0 else 0
            verdict = "scale" if roas >= 4.0 else "hold" if roas >= 3.0 else "cut" if roas >= 2.0 else "pause"
            roas_report.append({
                "segment": seg,
                "spend": row["spend"],
                "revenue": revenue,
                "roas": roas,
                "verdict": verdict,
            })

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data={"roas_report": roas_report, "date_range": task.get("date_range", "last_7_days")},
            items_processed=len(roas_report),
            items_total=len(roas_report),
        )


# ─────────────────────────────────────────────
# Meta Ads Agent (GPT-5)
# ─────────────────────────────────────────────

class MetaAdsAgent(BaseAgent):
    """Adjusts Meta (FB/IG) bids and audience targeting."""

    def __init__(self):
        super().__init__("meta_ads")

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        audience = task.get("audience", {})
        segments = audience.get("segments", [])

        await self.simulate_latency(400)
        self.simulate_token_usage(6000, 1500)

        actions = []
        for seg in segments[:3]:
            action = seg.get("recommended_action", "hold")
            actions.append({
                "platform": "meta",
                "segment_id": seg.get("segment_id", "unknown"),
                "action": action,
                "bid_change_pct": {"scale": 40, "hold": 0, "cut": -30, "pause": -100}.get(action, 0),
            })

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data={"platform": "meta", "actions": actions},
            items_processed=len(actions),
            items_total=len(segments),
        )


# ─────────────────────────────────────────────
# Google Ads Agent (GPT-5)
# ─────────────────────────────────────────────

class GoogleAdsAgent(BaseAgent):
    """Adjusts Google keyword bids and negative keywords."""

    def __init__(self):
        super().__init__("google_ads")

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        audience = task.get("audience", {})
        segments = audience.get("segments", [])

        await self.simulate_latency(350)
        self.simulate_token_usage(5500, 1200)

        actions = []
        for seg in segments[:3]:
            action = seg.get("recommended_action", "hold")
            actions.append({
                "platform": "google",
                "segment_id": seg.get("segment_id", "unknown"),
                "action": action,
                "keyword_adjustments": random.randint(2, 8),
            })

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data={"platform": "google", "actions": actions},
            items_processed=len(actions),
            items_total=len(segments),
        )


# ─────────────────────────────────────────────
# LinkedIn Ads Agent (GPT-5)
# ─────────────────────────────────────────────

class LinkedInAdsAgent(BaseAgent):
    """Adjusts LinkedIn job title targeting and lead gen forms."""

    def __init__(self):
        super().__init__("linkedin_ads")

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        audience = task.get("audience", {})
        segments = audience.get("segments", [])

        await self.simulate_latency(300)
        self.simulate_token_usage(4000, 800)

        actions = []
        for seg in segments[:2]:
            actions.append({
                "platform": "linkedin",
                "segment_id": seg.get("segment_id", "unknown"),
                "action": seg.get("recommended_action", "hold"),
                "targeting_update": "job_title_refined",
            })

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data={"platform": "linkedin", "actions": actions},
            items_processed=len(actions),
            items_total=len(segments),
        )


# ─────────────────────────────────────────────
# Creative Agent (Gemini 3 Pro)
# ─────────────────────────────────────────────

class CreativeAgent(BaseAgent):
    """Analyzes ad performance and generates new copy per segment."""

    def __init__(self):
        super().__init__("creative")

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        audience = task.get("audience", {})
        segments = audience.get("segments", [])

        creatives = []
        total = min(len(segments), 4)

        for i, seg in enumerate(segments[:total]):
            if not self.check_budget(budget, estimated_unit_cost=3500):
                return self.make_result(
                    status=CompletionStatus.PARTIAL_SAFE,
                    data={"creatives": creatives},
                    items_processed=i,
                    items_total=total,
                    checkpoint={"completed": [c["segment_id"] for c in creatives]},
                )

            await self.simulate_latency(400)
            self.simulate_token_usage(3500, 800)

            seg_id = seg.get("segment_id", f"segment_{i}")
            creatives.append({
                "segment_id": seg_id,
                "headline": f"Special offer for {seg_id.replace('_', ' ').title()}",
                "body": f"Targeted copy for the {seg_id} audience segment.",
                "cta": random.choice(["Book Now", "Learn More", "Get Started", "Claim Offer"]),
            })

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data={"creatives": creatives},
            items_processed=total,
            items_total=total,
        )


# ─────────────────────────────────────────────
# Reporting Agent (Claude Haiku 4.5)
# ─────────────────────────────────────────────

class ReportingAgent(BaseAgent):
    """Compresses pipeline results into a digest."""

    def __init__(self):
        super().__init__("reporting")

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        await self.simulate_latency(200)
        self.simulate_token_usage(3500, 700)

        warnings = task.get("warnings", [])
        total_tokens = task.get("total_tokens", 0)

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data={
                "digest": {
                    "top_insight": "Past customers segment has highest ROAS (9.0x) — recommend 40% budget increase",
                    "platforms_optimized": ["meta", "google", "linkedin"],
                    "warnings_count": len(warnings),
                    "total_tokens_used": total_tokens,
                    "next_run": "scheduled in 8 hours",
                },
            },
            items_processed=1,
            items_total=1,
        )
