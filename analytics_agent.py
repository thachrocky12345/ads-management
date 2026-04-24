"""
agents/analytics_agent.py  [REBUILT]
──────────────────────────────────────
Analytics Agent — GA4 + Claude Sonnet 4.5

Pipeline:
  Turn 1 — Fetch spend data (Meta + Google + LinkedIn APIs)  [mock — add your connectors]
  Turn 2 — Fetch GA4 revenue + conversion data
  Turn 3 — Claude joins the data, calculates ROAS, and produces anomaly analysis

The join step (Turn 3) is ATOMIC:
  If there's insufficient budget to complete it, we return PARTIAL_UNSAFE.
  A half-joined ROAS table is actively dangerous — worse than no data.

Real Claude call replaces the heuristic join logic from v1.
"""

import os
import json
import logging
from dataclasses import dataclass
from typing import Optional

from core.types import AgentResult, TokenBudget
from core.llm_client import LLMClient
from core.ga4_client import GA4Client, GA4ConversionRecord
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

TOKENS_SPEND_FETCH   = 1_200   # Turn 1: fetch + format spend data
TOKENS_REVENUE_FETCH = 1_500   # Turn 2: fetch + format GA4 data
TOKENS_LLM_JOIN      = 5_500   # Turn 3: Claude join + analysis (most expensive)


# ── Prompts ──────────────────────────────────────────────────────────────────

ANALYTICS_SYSTEM = """You are a senior performance marketing analyst for a local SMB 
running paid ads on Meta, Google, and LinkedIn.

You receive spend data from ad platforms and revenue data from Google Analytics 4.
Your job is to join these datasets by segment, calculate ROAS, and surface insights 
that drive immediate budget decisions.

Rules:
- Flag any segment below 3.0x ROAS as underperforming
- Flag any segment above 5.0x ROAS as a scaling opportunity
- Note anomalies: segments with high spend but zero conversions
- Be specific — dollar amounts, percentages, platform names
- Output only the JSON format requested
"""

JOIN_PROMPT = """Join the spend and revenue data below and calculate ROAS per segment.
Then analyse the results for a local SMB ads manager.

AD SPEND DATA (last {lookback_days} days, across Meta + Google + LinkedIn):
{spend_data}

GA4 REVENUE DATA (last {lookback_days} days):
{ga4_data}

JOIN LOGIC:
- Match spend records to GA4 records using campaign name / segment name
- If a spend record has no matching GA4 record, mark revenue as $0
- Calculate ROAS = revenue / spend for each matched record
- Where segment appears on multiple platforms, calculate per-platform and combined

Return a JSON object with exactly these keys:
{{
  "roas_records": [
    {{
      "segment_id": <string>,
      "segment_name": <string>,
      "platform": <"meta" | "google" | "linkedin" | "combined">,
      "spend_usd": <float>,
      "revenue_usd": <float>,
      "roas": <float>,
      "conversions": <int>,
      "verdict": <"scale" | "hold" | "cut" | "pause">,
      "action": <specific action string, e.g. "Increase budget 40%" or "Pause — no conversions">
    }}
  ],
  "total_spend_usd": <float>,
  "total_revenue_usd": <float>,
  "blended_roas": <float>,
  "top_performer": <segment_name of highest ROAS segment>,
  "worst_performer": <segment_name of lowest ROAS segment>,
  "anomalies": [<list of strings describing anything unusual>],
  "analyst_summary": <2-3 sentences: key takeaways and recommended immediate actions>
}}"""


@dataclass
class ROASRecord:
    segment_id:   str
    segment_name: str
    platform:     str
    spend_usd:    float
    revenue_usd:  float
    roas:         float
    conversions:  int
    verdict:      str
    action:       str


@dataclass
class AnalyticsResult:
    roas_records:       list[ROASRecord]
    total_spend_usd:    float
    total_revenue_usd:  float
    blended_roas:       float
    top_performer:      str
    worst_performer:    str
    anomalies:          list[str]
    analyst_summary:    str


class AnalyticsAgent(BaseAgent):
    """
    Produces ROAS per segment using GA4 revenue + ad platform spend.
    Claude performs the join and analysis in Turn 3.

    PARTIAL_UNSAFE logic:
    - Turn 1 alone (spend data only)  → not useful, PARTIAL_UNSAFE
    - Turn 2 alone (revenue only)     → not useful, PARTIAL_UNSAFE
    - Both but no Turn 3 join         → data present but unjoined, PARTIAL_UNSAFE
    - All 3 turns complete            → COMPLETE
    """

    def __init__(self):
        super().__init__("analytics")
        self._llm      = LLMClient(agent_id="analytics")
        self._ga4      = GA4Client()
        self._lookback = int(os.getenv("ANALYSIS_LOOKBACK_DAYS", "7"))

    def _execute(
        self,
        task_id:     str,
        budget:      TokenBudget,
        resume_from: Optional[dict],
    ) -> AgentResult:

        # ── Turn 1: Fetch ad spend data ───────────────────────────────
        if not self.check_budget(TOKENS_SPEND_FETCH):
            return self._make_partial_unsafe(
                task_id,
                "Insufficient budget to fetch spend data — cannot start analysis."
            )

        spend_records = self._fetch_spend_data()
        self.consume_tokens(TOKENS_SPEND_FETCH)
        self.save_checkpoint({"phase": "spend_fetched", "spend": spend_records})
        logger.info(
            f"[{self.agent_id}] Turn 1 done: "
            f"{len(spend_records)} spend records across platforms"
        )

        # ── Turn 2: Fetch GA4 revenue data ────────────────────────────
        if not self.check_budget(TOKENS_REVENUE_FETCH):
            # Spend data alone is useless for ROAS — unsafe partial
            return self._make_partial_unsafe(
                task_id,
                "Budget exhausted after spend fetch. "
                "Cannot complete GA4 revenue pull. "
                "Spend-only data cannot produce ROAS. Retry with expanded budget."
            )

        ga4_records = self._ga4.get_conversions_by_campaign(self._lookback)
        self.consume_tokens(TOKENS_REVENUE_FETCH)
        self.save_checkpoint({
            "phase":   "revenue_fetched",
            "spend":   spend_records,
            "revenue": [vars(r) for r in ga4_records],
        })
        logger.info(
            f"[{self.agent_id}] Turn 2 done: "
            f"{len(ga4_records)} GA4 conversion records"
        )

        # ── Turn 3: Claude joins + analyses ───────────────────────────
        # This is ATOMIC — do not start if budget is insufficient.
        # An incomplete join is worse than no join.
        if not self.check_budget(TOKENS_LLM_JOIN):
            return self._make_partial_unsafe(
                task_id,
                "Budget exhausted before Claude join step. "
                "Have spend and revenue data separately but join is incomplete. "
                "Unjoined data cannot produce ROAS per segment. "
                "Retry with expanded budget — need ~5,500 tokens for join."
            )

        logger.info(f"[{self.agent_id}] Turn 3: Sending to Claude for join + analysis...")
        analytics_result = self._llm_join_and_analyse(spend_records, ga4_records)
        self.consume_tokens(TOKENS_LLM_JOIN)

        logger.info(
            f"[{self.agent_id}] Turn 3 done: "
            f"{len(analytics_result.roas_records)} ROAS records | "
            f"blended ROAS={analytics_result.blended_roas:.2f}x"
        )

        return self._make_complete(
            task_id=task_id,
            data=analytics_result,
            total=len(analytics_result.roas_records),
        )

    # ─────────────────────────────────────────
    # LLM join + analysis (Turn 3)
    # ─────────────────────────────────────────

    def _llm_join_and_analyse(
        self,
        spend:   list[dict],
        ga4:     list[GA4ConversionRecord],
    ) -> AnalyticsResult:

        spend_formatted = json.dumps(spend, indent=2)
        ga4_formatted   = json.dumps(
            [
                {
                    "campaign":        r.campaign,
                    "source_medium":   r.source_medium,
                    "sessions":        r.sessions,
                    "conversions":     r.conversions,
                    "revenue_usd":     r.revenue_usd,
                    "avg_order_value": r.avg_order_value,
                }
                for r in ga4
            ],
            indent=2,
        )

        result_json, _ = self._llm.call_json(
            system_prompt=ANALYTICS_SYSTEM + "\n\n" + self._budget.to_prompt_block(),
            user_message=JOIN_PROMPT.format(
                lookback_days=self._lookback,
                spend_data=spend_formatted,
                ga4_data=ga4_formatted,
            ),
            expected_keys=[
                "roas_records", "total_spend_usd", "total_revenue_usd",
                "blended_roas", "top_performer", "worst_performer",
                "anomalies", "analyst_summary",
            ],
            max_tokens=1_500,
        )

        roas_records = [
            ROASRecord(
                segment_id=r.get("segment_id", f"seg_{i}"),
                segment_name=r["segment_name"],
                platform=r["platform"],
                spend_usd=float(r["spend_usd"]),
                revenue_usd=float(r["revenue_usd"]),
                roas=float(r["roas"]),
                conversions=int(r.get("conversions", 0)),
                verdict=r["verdict"],
                action=r.get("action", ""),
            )
            for i, r in enumerate(result_json["roas_records"])
        ]

        return AnalyticsResult(
            roas_records=roas_records,
            total_spend_usd=float(result_json["total_spend_usd"]),
            total_revenue_usd=float(result_json["total_revenue_usd"]),
            blended_roas=float(result_json["blended_roas"]),
            top_performer=result_json["top_performer"],
            worst_performer=result_json["worst_performer"],
            anomalies=result_json.get("anomalies", []),
            analyst_summary=result_json["analyst_summary"],
        )

    # ─────────────────────────────────────────
    # Spend data fetcher
    # Replace _fetch_spend_data() with real
    # Meta / Google / LinkedIn API calls.
    # ─────────────────────────────────────────

    def _fetch_spend_data(self) -> list[dict]:
        """
        In production, call:
          - Meta Marketing API: /act_{ad_account_id}/insights
          - Google Ads API:     campaigns.list + metrics
          - LinkedIn Ads API:   /adAnalytics

        Each platform returns spend by campaign → map to segment name
        using your UTM campaign naming convention.

        Returns list of dicts with keys:
          segment_id, segment_name, platform, spend_usd, impressions, clicks
        """
        # ── Demo data (replace with real API calls) ───────────────────
        return [
            # Meta
            {"segment_id": "seg_1", "segment_name": "past_customers_email",    "platform": "meta",     "spend_usd":  90.0, "impressions":  4_200, "clicks": 180},
            {"segment_id": "seg_2", "segment_name": "website_retarget_30d",    "platform": "meta",     "spend_usd": 180.0, "impressions": 12_400, "clicks": 340},
            {"segment_id": "seg_3", "segment_name": "lookalike_top5pct",       "platform": "meta",     "spend_usd": 220.0, "impressions": 38_000, "clicks": 520},
            {"segment_id": "seg_5", "segment_name": "cold_interest_homedecor", "platform": "meta",     "spend_usd": 150.0, "impressions": 95_000, "clicks": 290},
            # Google
            {"segment_id": "seg_4", "segment_name": "local_radius_search",     "platform": "google",   "spend_usd": 310.0, "impressions": 22_000, "clicks": 410},
            {"segment_id": "seg_2", "segment_name": "website_retarget_30d",    "platform": "google",   "spend_usd":  80.0, "impressions":  5_200, "clicks": 120},
            # LinkedIn
            {"segment_id": "seg_6", "segment_name": "linkedin_office_mgr",     "platform": "linkedin", "spend_usd": 200.0, "impressions":  3_100, "clicks":  42},
        ]
