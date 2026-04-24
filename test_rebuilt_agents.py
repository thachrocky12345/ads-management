"""
tests/test_rebuilt_agents.py
─────────────────────────────
Tests for the rebuilt agents using mocked LLM + API clients.
No real API calls needed — all external services are patched.

Run: python -m pytest tests/test_rebuilt_agents.py -v
"""

import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import asdict

from core.types import CompletionStatus, TokenBudget
from core.budget_manager import TokenBudgetManager


# ── Shared fixtures ────────────────────────────────────────────────────────

def normal_budget(agent_id="analytics"):
    return TokenBudgetManager().assign(agent_id, complexity="normal")

def tight_budget(input_tokens=3_000):
    return TokenBudget(
        input_tokens=input_tokens,
        output_tokens=1_000,
        max_turns=2,
        safety_margin=200,
    )

MOCK_SEGMENT_SCORE = {
    "roas_prediction": 5.3,
    "ltv_score":       7.2,
    "priority":        "scale",
    "budget_rec":      "increase 30%",
    "targeting_notes": "High-intent segment with strong conversion history.",
    "ad_copy_angles":  ["Save time on cleaning", "Trusted by local businesses"],
}

MOCK_STRATEGY = {
    "targeting_strategy":
        "Focus 60% of budget on past customers and retargeting. "
        "Test lookalike expansion at 20%. Pause cold interest targeting.",
    "top_segment_id":     "hs_seg_1",
    "lookalike_seed_ids": ["hs_seg_2"],
    "key_insight":        "Past customers convert at 9x — dramatically outperform cold audiences.",
}

MOCK_ROAS_RESULT = {
    "roas_records": [
        {"segment_id": "seg_1", "segment_name": "past_customers_email",
         "platform": "meta", "spend_usd": 90.0, "revenue_usd": 810.0,
         "roas": 9.0, "conversions": 8, "verdict": "scale",
         "action": "Increase budget 40%"},
        {"segment_id": "seg_2", "segment_name": "website_retarget_30d",
         "platform": "meta", "spend_usd": 180.0, "revenue_usd": 960.0,
         "roas": 5.3, "conversions": 12, "verdict": "scale",
         "action": "Increase budget 20%"},
        {"segment_id": "seg_5", "segment_name": "cold_interest_homedecor",
         "platform": "meta", "spend_usd": 150.0, "revenue_usd": 180.0,
         "roas": 1.2, "conversions": 2, "verdict": "pause",
         "action": "Pause — below 3x ROAS threshold"},
    ],
    "total_spend_usd":   420.0,
    "total_revenue_usd": 1_950.0,
    "blended_roas":      4.64,
    "top_performer":     "past_customers_email",
    "worst_performer":   "cold_interest_homedecor",
    "anomalies":         ["LinkedIn campaign has zero conversions despite $200 spend"],
    "analyst_summary":   "Past customers and retargeting driving strong returns. "
                         "Cold interest should be paused immediately.",
}


# ────────────────────────────────────────────────────────────────────────────
# Analytics Agent Tests
# ────────────────────────────────────────────────────────────────────────────

class TestAnalyticsAgentRebuilt:

    def _make_agent_with_mocks(self, llm_response=None):
        """Create AnalyticsAgent with all external calls mocked."""
        from agents.analytics_agent import AnalyticsAgent

        agent = AnalyticsAgent()

        # Mock GA4 client
        agent._ga4 = MagicMock()
        agent._ga4.get_conversions_by_campaign.return_value = []

        # Mock LLM client
        agent._llm = MagicMock()
        agent._llm.call_json.return_value = (
            llm_response or MOCK_ROAS_RESULT, 4_800
        )

        return agent

    def test_complete_run_returns_roas_records(self):
        agent  = self._make_agent_with_mocks()
        result = agent.run("t1", normal_budget("analytics"))

        assert result.status == CompletionStatus.COMPLETE
        assert result.data is not None
        assert len(result.data.roas_records) == 3
        assert result.data.blended_roas == 4.64

    def test_llm_called_exactly_once_for_join(self):
        agent = self._make_agent_with_mocks()
        agent.run("t1", normal_budget("analytics"))
        assert agent._llm.call_json.call_count == 1

    def test_analyst_summary_in_result(self):
        agent  = self._make_agent_with_mocks()
        result = agent.run("t1", normal_budget("analytics"))
        assert len(result.data.analyst_summary) > 10

    def test_top_and_worst_performer_populated(self):
        agent  = self._make_agent_with_mocks()
        result = agent.run("t1", normal_budget("analytics"))
        assert result.data.top_performer   == "past_customers_email"
        assert result.data.worst_performer == "cold_interest_homedecor"

    def test_anomalies_surfaced(self):
        agent  = self._make_agent_with_mocks()
        result = agent.run("t1", normal_budget("analytics"))
        assert len(result.data.anomalies) >= 1

    def test_budget_too_tight_for_join_returns_partial_unsafe(self):
        """If budget runs out before Turn 3 (join), result must be PARTIAL_UNSAFE."""
        agent = self._make_agent_with_mocks()
        # Budget: enough for T1 + T2 but not T3 (needs ~5,500)
        result = agent.run("t1", tight_budget(input_tokens=4_000))
        assert result.status == CompletionStatus.PARTIAL_UNSAFE

    def test_unsafe_data_is_always_none(self):
        """PARTIAL_UNSAFE must never expose the partial data downstream."""
        agent  = self._make_agent_with_mocks()
        result = agent.run("t1", tight_budget(input_tokens=4_000))
        assert result.data is None

    def test_ga4_client_called_in_turn2(self):
        agent = self._make_agent_with_mocks()
        agent.run("t1", normal_budget("analytics"))
        agent._ga4.get_conversions_by_campaign.assert_called_once()

    def test_verdict_distribution_is_correct(self):
        agent  = self._make_agent_with_mocks()
        result = agent.run("t1", normal_budget("analytics"))
        verdicts = [r.verdict for r in result.data.roas_records]
        assert "scale" in verdicts
        assert "pause" in verdicts

    def test_roas_calculation_matches_llm_output(self):
        agent  = self._make_agent_with_mocks()
        result = agent.run("t1", normal_budget("analytics"))
        seg1   = next(r for r in result.data.roas_records if r.segment_id == "seg_1")
        assert seg1.roas == 9.0
        assert seg1.spend_usd == 90.0
        assert seg1.revenue_usd == 810.0


# ────────────────────────────────────────────────────────────────────────────
# Audience Intel Agent Tests
# ────────────────────────────────────────────────────────────────────────────

class TestAudienceIntelAgentRebuilt:

    def _make_agent_with_mocks(self, n_segments=4):
        from agents.audience_intel_agent import AudienceIntelAgent
        from core.hubspot_client import HubSpotSegment
        from core.ga4_client import GA4ConversionRecord

        agent = AudienceIntelAgent()

        # Mock HubSpot
        agent._hubspot = MagicMock()
        agent._hubspot.get_customer_segments.return_value = [
            HubSpotSegment(
                id=f"hs_seg_{i}",
                name=f"Test Segment {i}",
                contact_count=100 + i * 50,
                avg_revenue=500.0 - i * 50,
                avg_deal_count=2.0,
                top_cities=["Chicago"],
                top_job_titles=["Homeowner"],
                source="crm_list",
            )
            for i in range(1, n_segments + 1)
        ]

        # Mock GA4
        agent._ga4 = MagicMock()
        agent._ga4.get_conversions_by_campaign.return_value = [
            GA4ConversionRecord(
                segment_id=f"seg_{i}",
                campaign=f"Test Segment {i}",
                source_medium="paid_social / meta",
                sessions=1000,
                conversions=20 - i,
                revenue_usd=1600.0 - i * 100,
                avg_order_value=80.0,
                date_range="2026-03-05 to 2026-03-12",
            )
            for i in range(1, n_segments + 1)
        ]

        # Mock LLM — return segment score for individual calls, strategy for last
        call_count = [0]

        def mock_call_json(system_prompt, user_message, expected_keys, max_tokens=1000):
            call_count[0] += 1
            if "targeting_strategy" in expected_keys:
                return MOCK_STRATEGY, 1_200
            return MOCK_SEGMENT_SCORE, 800

        agent._llm = MagicMock()
        agent._llm.call_json.side_effect = mock_call_json

        return agent

    def test_complete_run_scores_all_segments(self):
        agent  = self._make_agent_with_mocks(n_segments=4)
        result = agent.run("t1", normal_budget("audience_intel"))

        assert result.status == CompletionStatus.COMPLETE
        assert result.items_processed == 4

    def test_each_segment_gets_one_llm_call_plus_synthesis(self):
        """4 segments → 4 scoring calls + 1 strategy call = 5 total"""
        agent = self._make_agent_with_mocks(n_segments=4)
        agent.run("t1", normal_budget("audience_intel"))
        assert agent._llm.call_json.call_count == 5

    def test_scored_segments_have_all_fields(self):
        agent  = self._make_agent_with_mocks(n_segments=2)
        result = agent.run("t1", normal_budget("audience_intel"))
        seg    = result.data.scored_segments[0]
        assert seg.roas_prediction == 5.3
        assert seg.priority        == "scale"
        assert seg.budget_rec      == "increase 30%"
        assert len(seg.ad_copy_angles) == 2

    def test_strategy_synthesised_from_all_segments(self):
        agent  = self._make_agent_with_mocks(n_segments=3)
        result = agent.run("t1", normal_budget("audience_intel"))
        assert result.data.targeting_strategy != ""
        assert result.data.top_segment_id == "hs_seg_1"

    def test_tight_budget_stops_cleanly_at_segment_boundary(self):
        """With very tight budget, agent should stop at a segment boundary
        and return partial_safe — never partial_unsafe."""
        agent = self._make_agent_with_mocks(n_segments=4)
        # Only enough for ~1 segment (2800 tokens each)
        result = agent.run("t1", tight_budget(input_tokens=5_500))

        assert result.status == CompletionStatus.PARTIAL_SAFE
        # Whatever was scored is correct — no corrupt data
        if isinstance(result.data, list):
            assert len(result.data) < 4

    def test_partial_safe_has_checkpoint(self):
        """Partial results must have checkpoint for retry."""
        agent  = self._make_agent_with_mocks(n_segments=4)
        result = agent.run("t1", tight_budget(input_tokens=5_500))
        if result.status == CompletionStatus.PARTIAL_SAFE:
            assert result.checkpoint is not None
            assert "scored_segments" in result.checkpoint["state"]

    def test_resume_from_checkpoint_skips_completed(self):
        """When resuming, already-scored segments must be skipped."""
        from agents.audience_intel_agent import ScoredSegment as SS

        agent = self._make_agent_with_mocks(n_segments=4)

        # Simulate a checkpoint that has 2 segments already done
        fake_checkpoint = {
            "state": {
                "scored_segments": [
                    SS(
                        segment_id="hs_seg_1",
                        segment_name="Test Segment 1",
                        contact_count=150,
                        source="crm_list",
                        conversions=19, revenue_usd=1_500.0,
                        conversion_rate=0.019, avg_order_value=80.0,
                        roas_prediction=5.3, ltv_score=7.2,
                        priority="scale", budget_rec="increase 30%",
                        targeting_notes="Good segment.",
                        ad_copy_angles=["angle 1"],
                    ),
                    SS(
                        segment_id="hs_seg_2",
                        segment_name="Test Segment 2",
                        contact_count=200,
                        source="crm_list",
                        conversions=18, revenue_usd=1_400.0,
                        conversion_rate=0.018, avg_order_value=80.0,
                        roas_prediction=4.8, ltv_score=6.5,
                        priority="scale", budget_rec="hold",
                        targeting_notes="Decent segment.",
                        ad_copy_angles=["angle 2"],
                    ),
                ],
                "completed_ids": ["hs_seg_1", "hs_seg_2"],
                "pending_ids":   ["hs_seg_3", "hs_seg_4"],
            }
        }

        result = agent.run(
            "t1_retry",
            normal_budget("audience_intel"),
            resume_from=fake_checkpoint,
        )

        # Should only have scored the 2 remaining + synthesis = 3 calls
        assert agent._llm.call_json.call_count == 3  # 2 remaining + 1 strategy

    def test_hubspot_and_ga4_both_called(self):
        agent = self._make_agent_with_mocks(n_segments=2)
        agent.run("t1", normal_budget("audience_intel"))
        agent._hubspot.get_customer_segments.assert_called_once()
        agent._ga4.get_conversions_by_campaign.assert_called_once()

    def test_total_addressable_audience_counts_scale_only(self):
        """total_addressable should only sum 'scale' priority segments."""
        agent  = self._make_agent_with_mocks(n_segments=4)
        result = agent.run("t1", normal_budget("audience_intel"))
        # All segments get MOCK_SEGMENT_SCORE which has priority="scale"
        expected = sum(100 + i * 50 for i in range(1, 5))
        assert result.data.total_addressable == expected
