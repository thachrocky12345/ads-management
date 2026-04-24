"""
agents/analytics_agent.py  [REBUILT]
─────────────────────────────────────
Analytics Agent — GA4 + GPT-5

Pipeline (3 turns):
  1. Pull spend data from ad platform APIs (or mock)
  2. Pull conversion/revenue data from GA4
  3. Join, calculate ROAS per segment, and score (atomic — PARTIAL_UNSAFE if interrupted)

The ROAS join step is atomic: if budget is too low to complete it,
returns PARTIAL_UNSAFE with data=None rather than half-calculated metrics.
"""

import logging
from typing import Optional

from core.models import AgentResult, CompletionStatus, TokenBudget
from core.llm_client import LLMClient
from core.ga4_client import GA4Client, GA4ConversionRecord
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

TOKENS_SPEND_PULL = 3_000
TOKENS_REVENUE_PULL = 3_000
TOKENS_ROAS_JOIN = 4_000

ROAS_ANALYSIS_PROMPT = """Analyse this ROAS report for an SMB running ads across Meta, Google, and LinkedIn.

RAW DATA:
{roas_data}

For each segment, determine:
1. Whether ROAS is above the 3.0x profitability threshold
2. The recommended action: "scale" (ROAS >= 4x), "hold" (3-4x), "cut" (2-3x), "pause" (<2x)
3. A brief reason for the recommendation

Return a JSON object with:
{{
  "roas_report": [
    {{
      "segment": "<name>",
      "spend": <float>,
      "revenue": <float>,
      "roas": <float>,
      "verdict": "<scale|hold|cut|pause>",
      "reason": "<1 sentence>"
    }}
  ],
  "top_insight": "<1 sentence: the most important finding>",
  "total_spend": <float>,
  "total_revenue": <float>,
  "blended_roas": <float>
}}"""


class AnalyticsAgentLLM(BaseAgent):
    """
    Pulls spend + revenue, joins to calculate ROAS per segment.
    Uses GPT-5 for the analysis step.

    The ROAS join is atomic — if there's not enough budget to
    complete it, the agent explicitly returns PARTIAL_UNSAFE.
    """

    def __init__(self):
        super().__init__("analytics")
        self._llm = LLMClient(agent_id="analytics")
        self._ga4 = GA4Client()

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        date_range = task.get("date_range", "last_7_days")
        lookback = 7 if "7" in date_range else 30

        # ── Turn 1: Pull spend data ──────────────────────────────────
        logger.info(f"[{self.agent_id}] Pulling spend data...")
        await self.simulate_latency(300)
        self.consume_tokens(TOKENS_SPEND_PULL)

        # In production, this would call Meta/Google/LinkedIn APIs
        spend_data = self._get_spend_data()

        # ── Turn 2: Pull revenue data from GA4 ──────────────────────
        if not self.check_budget(budget, estimated_unit_cost=TOKENS_REVENUE_PULL):
            # Can't pull revenue — ROAS join is impossible
            return self.make_result(
                status=CompletionStatus.PARTIAL_UNSAFE,
                data=None,
                error="Budget too low for revenue pull — cannot calculate ROAS without revenue data",
            )

        logger.info(f"[{self.agent_id}] Pulling GA4 conversion data ({lookback}d)...")
        await self.simulate_latency(300)
        self.consume_tokens(TOKENS_REVENUE_PULL)

        ga4_records = self._ga4.get_conversions_by_campaign(lookback)
        revenue_by_campaign = {r.campaign: r for r in ga4_records}

        # ── Turn 3: Join and calculate ROAS (ATOMIC) ─────────────────
        if not self.check_budget(budget, estimated_unit_cost=TOKENS_ROAS_JOIN):
            # Can't complete the join — return PARTIAL_UNSAFE
            return self.make_result(
                status=CompletionStatus.PARTIAL_UNSAFE,
                data=None,
                error="Budget too low for ROAS join — cannot return half-calculated metrics",
            )

        logger.info(f"[{self.agent_id}] Calculating ROAS per segment...")
        await self.simulate_latency(200)

        # Join spend + revenue
        raw_roas = []
        for row in spend_data:
            seg_name = row["segment"]
            ga4 = revenue_by_campaign.get(seg_name)
            revenue = ga4.revenue_usd if ga4 else 0
            roas = round(revenue / row["spend"], 2) if row["spend"] > 0 else 0

            raw_roas.append({
                "segment": seg_name,
                "spend": row["spend"],
                "revenue": revenue,
                "roas": roas,
            })

        # Use LLM to analyze the ROAS data
        roas_analysis, tokens = self._llm.call_json(
            system_prompt="You are a data analytics agent for SMB advertising.",
            user_message=ROAS_ANALYSIS_PROMPT.format(roas_data=raw_roas),
            expected_keys=["roas_report", "top_insight", "total_spend", "total_revenue", "blended_roas"],
            max_tokens=800,
        )
        self.consume_tokens(TOKENS_ROAS_JOIN)

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data={
                "roas_report": roas_analysis.get("roas_report", raw_roas),
                "top_insight": roas_analysis.get("top_insight", ""),
                "total_spend": roas_analysis.get("total_spend", sum(r["spend"] for r in raw_roas)),
                "total_revenue": roas_analysis.get("total_revenue", sum(r["revenue"] for r in raw_roas)),
                "blended_roas": roas_analysis.get("blended_roas", 0),
                "date_range": date_range,
            },
            items_processed=len(raw_roas),
            items_total=len(raw_roas),
        )

    @staticmethod
    def _get_spend_data() -> list[dict]:
        """
        Pull spend data from ad platforms.
        In production, this calls Meta/Google/LinkedIn APIs.
        Returns mock data for development.
        """
        return [
            {"segment": "Past Customers (Repeat Buyers)", "spend": 90.0, "clicks": 120, "platform": "meta"},
            {"segment": "Women 35-44 / Local 10km", "spend": 180.0, "clicks": 340, "platform": "meta"},
            {"segment": "Lookalike of Top 20% Customers", "spend": 220.0, "clicks": 280, "platform": "meta"},
            {"segment": "Men 25-34 / Broad Interest", "spend": 310.0, "clicks": 190, "platform": "google"},
            {"segment": "Cold Interest: Home Services", "spend": 150.0, "clicks": 85, "platform": "google"},
        ]
