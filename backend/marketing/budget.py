"""
marketing/budget.py
────────────────────
Budget allocation recommendations for AskLongevity.ai.
Strategy: Maximize organic (SEO) first — it compounds. Paid amplifies proven content.

INTEGRATION POINTS:
  - Replace mock CPC figures with real data from Google Ads API + Meta API
  - expected_conversions: calibrate using actual conversion rate from landing page analytics
"""

from pydantic import BaseModel


class ChannelAllocation(BaseModel):
    channel: str
    monthly_budget: float
    pct_of_total: float
    expected_clicks: int
    expected_cpc: float
    expected_conversions: int
    rationale: str
    priority: int


class BudgetPlan(BaseModel):
    total_budget: float
    allocations: list[ChannelAllocation]
    total_expected_clicks: int
    expected_monthly_signups: int
    cost_per_signup: float
    notes: str


def generate_budget_plan(monthly_budget: float) -> BudgetPlan:
    allocations: list[ChannelAllocation] = []

    if monthly_budget <= 200:
        allocations = [
            ChannelAllocation(
                channel="SEO Content Tools (contentswift + crawl4ai)",
                monthly_budget=round(monthly_budget * 0.70, 2),
                pct_of_total=70.0,
                expected_clicks=int(monthly_budget * 8),
                expected_cpc=0.0,
                expected_conversions=int(monthly_budget * 0.6),
                rationale="At this budget, organic SEO compounds over time. Every dollar in content returns 5–10x over 12 months vs paid's one-time return.",
                priority=1,
            ),
            ChannelAllocation(
                channel="SerpBear + GSC Setup",
                monthly_budget=round(monthly_budget * 0.30, 2),
                pct_of_total=30.0,
                expected_clicks=0,
                expected_cpc=0.0,
                expected_conversions=0,
                rationale="Rank tracking infrastructure pays back by guiding content investment to highest-ROI keywords.",
                priority=2,
            ),
        ]
        total_clicks = int(monthly_budget * 8)
        signups = max(1, int(total_clicks * 0.08))

    elif monthly_budget <= 500:
        seo = monthly_budget * 0.80
        social = monthly_budget * 0.20
        allocations = [
            ChannelAllocation(
                channel="SEO & Content Tools",
                monthly_budget=round(seo, 2), pct_of_total=80.0,
                expected_clicks=int(seo * 6), expected_cpc=0.0,
                expected_conversions=int(seo * 0.4),
                rationale="Pillar content and technical SEO fixes yield 3–6 month compounding returns. Prioritize over paid at this budget level.",
                priority=1,
            ),
            ChannelAllocation(
                channel="X/Twitter Promotion",
                monthly_budget=round(social, 2), pct_of_total=20.0,
                expected_clicks=int(social / 0.12), expected_cpc=0.12,
                expected_conversions=int((social / 0.12) * 0.03),
                rationale="X/Twitter longevity community has high organic amplification. Small paid boost on top-performing organic posts.",
                priority=2,
            ),
        ]
        total_clicks = int(seo * 6) + int(social / 0.12)
        signups = max(2, int(total_clicks * 0.065))

    elif monthly_budget <= 1000:
        seo = monthly_budget * 0.60
        meta = monthly_budget * 0.25
        google = monthly_budget * 0.15
        allocations = [
            ChannelAllocation(
                channel="SEO & Content Tools",
                monthly_budget=round(seo, 2), pct_of_total=60.0,
                expected_clicks=int(seo * 5), expected_cpc=0.0,
                expected_conversions=int(seo * 0.35),
                rationale="Still the highest ROI channel at this budget. Fully fund pillar content strategy and contentswift subscriptions.",
                priority=1,
            ),
            ChannelAllocation(
                channel="Meta Retargeting (FB + Instagram)",
                monthly_budget=round(meta, 2), pct_of_total=25.0,
                expected_clicks=int(meta / 0.55), expected_cpc=0.55,
                expected_conversions=int((meta / 0.55) * 0.05),
                rationale="Retargeting site visitors converts at 5–8x higher rate than cold traffic. Use custom audiences from site pixel.",
                priority=2,
            ),
            ChannelAllocation(
                channel="Google Ads (Brand + Category)",
                monthly_budget=round(google, 2), pct_of_total=15.0,
                expected_clicks=int(google / 1.90), expected_cpc=1.90,
                expected_conversions=int((google / 1.90) * 0.04),
                rationale="Brand campaign protects your name from competitor ads. Category ('longevity AI') captures commercial-intent searchers.",
                priority=3,
            ),
        ]
        total_clicks = int(seo * 5) + int(meta / 0.55) + int(google / 1.90)
        signups = max(5, int(total_clicks * 0.052))

    elif monthly_budget <= 2000:
        seo = monthly_budget * 0.40
        meta = monthly_budget * 0.30
        google = monthly_budget * 0.20
        twitter = monthly_budget * 0.10
        allocations = [
            ChannelAllocation(channel="SEO & Content Tools", monthly_budget=round(seo, 2), pct_of_total=40.0,
                              expected_clicks=int(seo * 4), expected_cpc=0.0, expected_conversions=int(seo * 0.30),
                              rationale="Content compound effect at scale. Fund 4 pillar pages/month plus technical audit tooling.", priority=1),
            ChannelAllocation(channel="Meta (Retargeting + Lookalike)", monthly_budget=round(meta, 2), pct_of_total=30.0,
                              expected_clicks=int(meta / 0.52), expected_cpc=0.52, expected_conversions=int((meta / 0.52) * 0.055),
                              rationale="Expand from retargeting to 1% lookalike audiences of your top converters.", priority=2),
            ChannelAllocation(channel="Google Ads (Search)", monthly_budget=round(google, 2), pct_of_total=20.0,
                              expected_clicks=int(google / 1.75), expected_cpc=1.75, expected_conversions=int((google / 1.75) * 0.045),
                              rationale="Scale to top longevity keyword clusters with proven landing page conversion.", priority=3),
            ChannelAllocation(channel="X/Twitter Promoted Posts", monthly_budget=round(twitter, 2), pct_of_total=10.0,
                              expected_clicks=int(twitter / 0.10), expected_cpc=0.10, expected_conversions=int((twitter / 0.10) * 0.025),
                              rationale="Amplify top-performing organic threads to biohacker + longevity audiences.", priority=4),
        ]
        total_clicks = int(seo * 4) + int(meta / 0.52) + int(google / 1.75) + int(twitter / 0.10)
        signups = max(10, int(total_clicks * 0.045))

    else:
        seo = monthly_budget * 0.30
        meta = monthly_budget * 0.35
        google = monthly_budget * 0.25
        twitter = monthly_budget * 0.10
        allocations = [
            ChannelAllocation(channel="SEO & Content Team/Tools", monthly_budget=round(seo, 2), pct_of_total=30.0,
                              expected_clicks=int(seo * 3.5), expected_cpc=0.0, expected_conversions=int(seo * 0.25),
                              rationale="At this budget, hire a longevity content writer ($800–1,200/mo) plus fund all SEO tools.", priority=1),
            ChannelAllocation(channel="Meta (Full Funnel)", monthly_budget=round(meta, 2), pct_of_total=35.0,
                              expected_clicks=int(meta / 0.48), expected_cpc=0.48, expected_conversions=int((meta / 0.48) * 0.058),
                              rationale="Run full funnel: awareness (video), consideration (carousel), conversion (retargeting). Test Reels for longevity content.", priority=2),
            ChannelAllocation(channel="Google Ads (Search + Display)", monthly_budget=round(google, 2), pct_of_total=25.0,
                              expected_clicks=int(google / 1.60), expected_cpc=1.60, expected_conversions=int((google / 1.60) * 0.048),
                              rationale="Add Display remarketing to Google Search. Use Customer Match with your email list.", priority=3),
            ChannelAllocation(channel="X/Twitter + Community", monthly_budget=round(twitter, 2), pct_of_total=10.0,
                              expected_clicks=int(twitter / 0.09), expected_cpc=0.09, expected_conversions=int((twitter / 0.09) * 0.028),
                              rationale="Sponsor top longevity creators + promoted posts. Consider Discord community sponsorships.", priority=4),
        ]
        total_clicks = int(seo * 3.5) + int(meta / 0.48) + int(google / 1.60) + int(twitter / 0.09)
        signups = max(20, int(total_clicks * 0.040))

    cost_per_signup = round(monthly_budget / signups, 2) if signups > 0 else 0.0

    return BudgetPlan(
        total_budget=monthly_budget,
        allocations=allocations,
        total_expected_clicks=total_clicks,
        expected_monthly_signups=signups,
        cost_per_signup=cost_per_signup,
        notes="Maximize organic SEO first — it compounds over time. Paid ads work best once your conversion rate is proven (>3%). Track all campaigns with UTM parameters.",
    )
