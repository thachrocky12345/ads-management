"""
marketing/channels.py
──────────────────────
Channel performance models and mock data for AskLongevity.ai.

INTEGRATION POINTS:
  - Google Organic: replace with GSC API (clicks, impressions, avg_position)
  - Google Ads: replace with Google Ads API (campaigns.list -> metrics)
  - Meta: replace with Meta Marketing API (insights endpoint)
  - X/Twitter: replace with Twitter API v2 (tweets/search/recent + analytics)
  - Discord: replace with Discord Bot API (guild.memberCount + webhook stats)
"""

from typing import Literal
from pydantic import BaseModel


class ChannelMetrics(BaseModel):
    channel_id: str
    name: str
    icon: str                           # Lucide icon name for frontend lookup
    status: Literal["active", "paused", "not_connected"]
    platform: Literal["google_organic", "google_ads", "meta", "twitter", "discord"]
    monthly_impressions: int | None = None
    monthly_clicks: int | None = None
    conversions: int | None = None
    spend_usd: float | None = None
    cpc: float | None = None
    roas: float | None = None
    ctr: float | None = None
    trend_pct: float | None = None      # Week-over-week % change
    top_content: str | None = None
    setup_difficulty: Literal["easy", "medium", "hard"]
    community_members: int | None = None
    weekly_posts: int | None = None
    referral_clicks: int | None = None
    notes: str | None = None


MOCK_CHANNELS: list[ChannelMetrics] = [
    ChannelMetrics(
        channel_id="google_organic",
        name="Google Organic",
        icon="Search",
        status="active",
        platform="google_organic",
        monthly_impressions=18_400,
        monthly_clicks=1_120,
        conversions=89,
        spend_usd=0.0,
        cpc=0.0,
        roas=None,
        ctr=0.061,
        trend_pct=12.5,
        top_content="Bryan Johnson Protocol Guide — 286 clicks",
        setup_difficulty="easy",
        notes="Primary free traffic driver. Avg position 24.3. Strong upward trend.",
    ),
    ChannelMetrics(
        channel_id="google_ads",
        name="Google Ads",
        icon="Target",
        status="not_connected",
        platform="google_ads",
        monthly_impressions=None,
        monthly_clicks=None,
        conversions=None,
        spend_usd=None,
        cpc=None,
        roas=None,
        ctr=None,
        trend_pct=None,
        top_content=None,
        setup_difficulty="hard",
        notes="Not yet configured. Recommended keywords: 'longevity AI', 'health AI assistant'. Est. CPC $1.80–$3.20.",
    ),
    ChannelMetrics(
        channel_id="meta",
        name="Meta (FB + Instagram)",
        icon="Globe",
        status="paused",
        platform="meta",
        monthly_impressions=8_600,
        monthly_clicks=312,
        conversions=14,
        spend_usd=180.0,
        cpc=0.58,
        roas=2.1,
        ctr=0.036,
        trend_pct=-4.2,
        top_content="'How AI is Revolutionizing Longevity' — 142 link clicks",
        setup_difficulty="medium",
        notes="Paused due to low ROAS. Recommend retargeting site visitors before resuming cold traffic.",
    ),
    ChannelMetrics(
        channel_id="twitter",
        name="X / Twitter",
        icon="Zap",
        status="active",
        platform="twitter",
        monthly_impressions=22_100,
        monthly_clicks=487,
        conversions=22,
        spend_usd=0.0,
        cpc=0.0,
        roas=None,
        ctr=0.022,
        trend_pct=31.4,
        top_content="'NAD+ vs NMN: The longevity debate' thread — 12.4K views",
        setup_difficulty="easy",
        notes="Strong organic reach in biohacker + longevity community. Fastest growing channel.",
    ),
    ChannelMetrics(
        channel_id="discord",
        name="Discord Community",
        icon="MessageCircle",
        status="active",
        platform="discord",
        monthly_impressions=None,
        monthly_clicks=None,
        conversions=None,
        spend_usd=0.0,
        cpc=None,
        roas=None,
        ctr=None,
        trend_pct=18.2,
        community_members=1_840,
        weekly_posts=47,
        referral_clicks=203,
        top_content="#longevity-research channel — highest engagement",
        setup_difficulty="easy",
        notes="Growing community. High-intent referral clicks (203/mo) despite small size.",
    ),
]
