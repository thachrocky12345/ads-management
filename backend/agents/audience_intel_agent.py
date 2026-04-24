"""
agents/audience_intel_agent.py  [REBUILT]
──────────────────────────────────────────
Audience Intel Agent — HubSpot CRM + GA4 + Claude Sonnet 4.5

Pipeline per segment:
  1. Load HubSpot CRM segments (first-party data)
  2. Enrich with GA4 conversion rates (actual revenue signal)
  3. Claude scores each segment: ROAS prediction, priority, budget rec
  4. Claude synthesises a cross-segment targeting strategy

Real LLM calls replace ALL mock scoring logic.
Budget-safe: checks token budget before each segment.
"""

import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

from core.models import AgentResult, CompletionStatus, TokenBudget
from core.llm_client import LLMClient
from core.hubspot_client import HubSpotClient, HubSpotSegment
from core.ga4_client import GA4Client, GA4ConversionRecord
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Conservative token estimate per segment (input + output for one Claude call)
TOKENS_PER_SEGMENT = 2_800
# Tokens for the final cross-segment strategy synthesis call
TOKENS_SYNTHESIS = 4_000


@dataclass
class ScoredSegment:
    segment_id: str
    segment_name: str
    contact_count: int
    source: str
    # GA4 signals
    conversions: int
    revenue_usd: float
    conversion_rate: float
    avg_order_value: float
    # Claude scores
    roas_prediction: float
    ltv_score: float
    priority: str           # "scale" | "hold" | "test" | "cut"
    budget_rec: str
    targeting_notes: str
    ad_copy_angles: list[str] = field(default_factory=list)


@dataclass
class AudienceIntelResult:
    scored_segments: list[dict]
    targeting_strategy: str
    top_segment_id: str
    lookalike_seed_ids: list[str]
    total_addressable: int


# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert digital advertising analyst specialising in
audience targeting for local SMB businesses running Meta, Google, and LinkedIn ads.

Your job is to analyse CRM and analytics data and produce precise, actionable
audience scoring for ad targeting decisions.

You always:
- Base scores on actual revenue and conversion data, not assumptions
- Give concrete, specific recommendations (not vague "consider testing")
- Think about LTV, not just immediate ROAS
- Flag when data is insufficient for strong recommendations
- Output exactly the JSON format requested — no preamble or commentary
"""

SEGMENT_SCORING_PROMPT = """Analyse this audience segment and score it for paid ad targeting.

SEGMENT DATA:
{segment_data}

GA4 CONVERSION DATA (last {lookback_days} days):
{ga4_data}

BUSINESS CONTEXT:
- Business type: Local SMB (service business)
- Active platforms: Meta Ads, Google Ads, LinkedIn Ads
- Target ROAS threshold: 3.0x (below this = unprofitable)
- Budget mode: optimise for profitable growth

Score this segment and return a JSON object with exactly these keys:
{{
  "roas_prediction": <float, predicted ROAS if we increase spend on this segment>,
  "ltv_score": <float 0-10, predicted lifetime value relative to other segments>,
  "priority": <"scale" | "hold" | "test" | "cut">,
  "budget_rec": <specific string like "increase 40%" or "pause" or "reduce 20%">,
  "targeting_notes": <2-3 sentences: why this score, what signal drives it>,
  "ad_copy_angles": <list of 2-3 short messaging angles tailored to this segment>
}}"""

STRATEGY_PROMPT = """You have scored {n} audience segments for an SMB running
Meta, Google, and LinkedIn ads. Here are all the scored segments:

{scored_segments_summary}

Now synthesise a cross-segment targeting strategy. Return a JSON object with:
{{
  "targeting_strategy": <3-4 sentences: overall approach, budget allocation logic,
                         which segments to prioritise and why>,
  "top_segment_id": <segment_id of the single best segment to prioritise>,
  "lookalike_seed_ids": <list of 1-3 segment_ids to use as lookalike seeds>,
  "key_insight": <1 sentence: the most important finding from this analysis>
}}"""


class AudienceIntelAgentLLM(BaseAgent):
    """
    Scores HubSpot CRM segments using GA4 conversion data and Claude.

    Each segment gets one Claude call (scoring).
    A final Claude call synthesises a cross-segment strategy.
    Budget is checked before EACH Claude call — never mid-call.
    """

    def __init__(self):
        super().__init__("audience_intel")
        self._llm = LLMClient(agent_id="audience_intel")
        self._hubspot = HubSpotClient()
        self._ga4 = GA4Client()
        self._lookback = int(os.getenv("ANALYSIS_LOOKBACK_DAYS", "7"))

    async def run(self, task: dict, budget: TokenBudget) -> AgentResult:
        # ── Load data sources ─────────────────────────────────────────
        logger.info(f"[{self.agent_id}] Fetching HubSpot segments...")
        hs_segments = self._hubspot.get_customer_segments()

        logger.info(f"[{self.agent_id}] Fetching GA4 conversions ({self._lookback}d)...")
        ga4_records = self._ga4.get_conversions_by_campaign(self._lookback)

        # Build GA4 lookup by segment name for enrichment
        ga4_by_campaign = {r.campaign: r for r in ga4_records}

        logger.info(
            f"[{self.agent_id}] Loaded {len(hs_segments)} HubSpot segments, "
            f"{len(ga4_records)} GA4 records"
        )

        # ── Resume from checkpoint if retrying ───────────────────────
        scored_so_far: list[ScoredSegment] = []
        completed_ids: set[str] = set()

        checkpoint = task.get("_checkpoint")
        if checkpoint:
            completed_ids = set(checkpoint.get("completed_ids", []))
            logger.info(
                f"[{self.agent_id}] Resuming: "
                f"{len(completed_ids)} segments already scored"
            )

        remaining = [s for s in hs_segments if s.id not in completed_ids]
        total = len(hs_segments)

        # ── Score each segment with a Claude call ─────────────────────
        for i, segment in enumerate(remaining):
            # Budget check BEFORE the Claude call
            if not self.check_budget(budget, estimated_unit_cost=TOKENS_PER_SEGMENT):
                logger.info(
                    f"[{self.agent_id}] Budget boundary: "
                    f"scored {len(scored_so_far)}/{total} segments"
                )
                return self.make_result(
                    status=CompletionStatus.PARTIAL_SAFE,
                    data={"segments": [asdict(s) for s in scored_so_far]},
                    items_processed=len(scored_so_far),
                    items_total=total,
                    checkpoint={
                        "completed_ids": list(completed_ids),
                        "pending_ids": [s.id for s in remaining[i:]],
                    },
                )

            # Enrich segment with GA4 data
            ga4 = ga4_by_campaign.get(segment.name)
            scored = self._score_segment_with_llm(segment, ga4)
            self.consume_tokens(TOKENS_PER_SEGMENT)

            scored_so_far.append(scored)
            completed_ids.add(segment.id)

            logger.info(
                f"[{self.agent_id}] Scored '{segment.name}': "
                f"ROAS={scored.roas_prediction:.1f}x | "
                f"{scored.priority} | {scored.budget_rec}"
            )

        # ── Synthesise cross-segment strategy ────────────────────────
        if not self.check_budget(budget, estimated_unit_cost=TOKENS_SYNTHESIS):
            logger.warning(
                f"[{self.agent_id}] No budget for strategy synthesis. "
                f"Returning scored segments without strategy."
            )
            return self.make_result(
                status=CompletionStatus.PARTIAL_SAFE,
                data={
                    "segments": [asdict(s) for s in scored_so_far],
                    "targeting_strategy": "Synthesis skipped — budget exhausted.",
                },
                items_processed=len(scored_so_far),
                items_total=total + 1,  # +1 for synthesis step
                checkpoint={"completed_ids": list(completed_ids)},
            )

        strategy = self._synthesise_strategy(scored_so_far)
        self.consume_tokens(TOKENS_SYNTHESIS)

        result_data = AudienceIntelResult(
            scored_segments=[asdict(s) for s in scored_so_far],
            targeting_strategy=strategy.get("targeting_strategy", ""),
            top_segment_id=strategy.get("top_segment_id", ""),
            lookalike_seed_ids=strategy.get("lookalike_seed_ids", []),
            total_addressable=sum(
                s.contact_count for s in scored_so_far if s.priority == "scale"
            ),
        )

        return self.make_result(
            status=CompletionStatus.COMPLETE,
            data=asdict(result_data),
            items_processed=total,
            items_total=total,
        )

    # ─────────────────────────────────────────
    # LLM calls
    # ─────────────────────────────────────────

    def _score_segment_with_llm(
        self,
        segment: HubSpotSegment,
        ga4: Optional[GA4ConversionRecord],
    ) -> ScoredSegment:
        """One Claude call per segment. Returns structured scoring."""

        segment_data = {
            "id": segment.id,
            "name": segment.name,
            "contact_count": segment.contact_count,
            "avg_ltv": f"${segment.avg_revenue:.0f}",
            "avg_deal_count": segment.avg_deal_count,
            "top_cities": segment.top_cities,
            "top_job_titles": segment.top_job_titles,
            "source": segment.source,
        }

        ga4_data = "No GA4 data available for this segment."
        conv_rate = 0.0
        revenue = 0.0
        aov = 0.0
        convs = 0

        if ga4:
            conv_rate = ga4.conversions / ga4.sessions if ga4.sessions > 0 else 0
            revenue = ga4.revenue_usd
            aov = ga4.avg_order_value
            convs = ga4.conversions
            ga4_data = {
                "sessions": ga4.sessions,
                "conversions": ga4.conversions,
                "conversion_rate": f"{conv_rate:.2%}",
                "revenue_usd": f"${ga4.revenue_usd:.0f}",
                "avg_order_value": f"${ga4.avg_order_value:.0f}",
                "source_medium": ga4.source_medium,
            }

        user_msg = SEGMENT_SCORING_PROMPT.format(
            segment_data=segment_data,
            ga4_data=ga4_data,
            lookback_days=self._lookback,
        )

        scored_json, _ = self._llm.call_json(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_msg,
            expected_keys=[
                "roas_prediction", "ltv_score", "priority",
                "budget_rec", "targeting_notes", "ad_copy_angles",
            ],
            max_tokens=600,
        )

        return ScoredSegment(
            segment_id=segment.id,
            segment_name=segment.name,
            contact_count=segment.contact_count,
            source=segment.source,
            conversions=convs,
            revenue_usd=revenue,
            conversion_rate=round(conv_rate, 4),
            avg_order_value=aov,
            roas_prediction=float(scored_json.get("roas_prediction", 0)),
            ltv_score=float(scored_json.get("ltv_score", 0)),
            priority=scored_json.get("priority", "hold"),
            budget_rec=scored_json.get("budget_rec", "hold"),
            targeting_notes=scored_json.get("targeting_notes", ""),
            ad_copy_angles=scored_json.get("ad_copy_angles", []),
        )

    def _synthesise_strategy(self, scored: list[ScoredSegment]) -> dict:
        """One Claude call to synthesise the cross-segment strategy."""

        summary = "\n".join([
            f"- {s.segment_name} (id={s.segment_id}): "
            f"ROAS={s.roas_prediction:.1f}x, LTV={s.ltv_score:.1f}/10, "
            f"priority={s.priority}, contacts={s.contact_count}, "
            f"revenue=${s.revenue_usd:.0f}, notes={s.targeting_notes}"
            for s in scored
        ])

        result, _ = self._llm.call_json(
            system_prompt=SYSTEM_PROMPT,
            user_message=STRATEGY_PROMPT.format(
                n=len(scored),
                scored_segments_summary=summary,
            ),
            expected_keys=[
                "targeting_strategy", "top_segment_id", "lookalike_seed_ids",
            ],
            max_tokens=600,
        )
        return result
