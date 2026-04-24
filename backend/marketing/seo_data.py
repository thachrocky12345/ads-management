"""
marketing/seo_data.py
──────────────────────
SEO data models and realistic mock data for AskLongevity.ai.

INTEGRATION POINTS:
  - overall_score: replace with crawl4ai site audit + Lighthouse scores averaged
  - monthly_impressions/clicks/avg_position: replace with Google Search Console API
    (google-searchconsole library: gsc.query(site, date_range, dimensions=['query']))
  - indexed_pages: replace with GSC index coverage report or google-indexing-script check
  - KeywordRanking: replace with SerpBear API (GET /api/keywords) for position tracking
  - ContentOpportunity: replace with contentswift gap analysis output
  - TechnicalIssue: replace with crawl4ai CrawlResult + Lighthouse JSON report
"""

from typing import Literal
from pydantic import BaseModel


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class SEOOverview(BaseModel):
    overall_score: int
    technical_score: int
    content_score: int
    authority_score: int
    monthly_impressions: int
    monthly_clicks: int
    avg_ctr: float
    avg_position: float
    indexed_pages: int
    wow_impressions_pct: float
    wow_clicks_pct: float
    wow_position_delta: float       # negative = improved (lower position = better)
    last_crawl_date: str


class KeywordRanking(BaseModel):
    keyword: str
    position: float
    impressions: int
    clicks: int
    ctr: float
    trend: Literal["up", "down", "stable"]
    difficulty: int                 # 1-100
    opportunity_score: int          # 1-100


class ContentOpportunity(BaseModel):
    keyword: str
    current_position: float | None  # None = not ranking yet
    potential_traffic_gain: int
    competition: Literal["low", "medium", "high"]
    suggested_content_type: str


class TechnicalIssue(BaseModel):
    severity: Literal["critical", "warning", "info"]
    category: Literal["speed", "crawl", "content", "structured_data"]
    title: str
    description: str
    pages_affected: int
    fix_effort: Literal["easy", "medium", "hard"]
    impact: Literal["high", "medium", "low"]
    tool_hint: str


class SEOAuditResult(BaseModel):
    score: int
    issues: list[TechnicalIssue]
    crawled_pages: int
    crawl_date: str


# ─────────────────────────────────────────────
# Mock Data — AskLongevity.ai
# ─────────────────────────────────────────────

MOCK_SEO_OVERVIEW = SEOOverview(
    overall_score=61,
    technical_score=54,
    content_score=68,
    authority_score=42,
    monthly_impressions=18_400,
    monthly_clicks=1_120,
    avg_ctr=0.061,
    avg_position=24.3,
    indexed_pages=87,
    wow_impressions_pct=8.2,
    wow_clicks_pct=12.5,
    wow_position_delta=-1.4,
    last_crawl_date="2026-04-20",
)

MOCK_KEYWORD_RANKINGS: list[KeywordRanking] = [
    KeywordRanking(keyword="longevity AI", position=7.2, impressions=3_200, clicks=198, ctr=0.062, trend="up", difficulty=38, opportunity_score=82),
    KeywordRanking(keyword="NAD+ benefits", position=14.1, impressions=5_800, clicks=180, ctr=0.031, trend="up", difficulty=52, opportunity_score=74),
    KeywordRanking(keyword="longevity supplements", position=19.4, impressions=8_200, clicks=142, ctr=0.017, trend="stable", difficulty=61, opportunity_score=68),
    KeywordRanking(keyword="healthspan optimization", position=11.6, impressions=2_100, clicks=98, ctr=0.047, trend="up", difficulty=34, opportunity_score=78),
    KeywordRanking(keyword="how to live longer", position=31.8, impressions=12_400, clicks=74, ctr=0.006, trend="down", difficulty=72, opportunity_score=55),
    KeywordRanking(keyword="longevity diet", position=22.3, impressions=4_600, clicks=66, ctr=0.014, trend="stable", difficulty=58, opportunity_score=62),
    KeywordRanking(keyword="biohacking longevity", position=9.1, impressions=1_800, clicks=112, ctr=0.062, trend="up", difficulty=41, opportunity_score=76),
    KeywordRanking(keyword="aging reversal science", position=16.7, impressions=2_900, clicks=58, ctr=0.020, trend="stable", difficulty=48, opportunity_score=64),
    KeywordRanking(keyword="Bryan Johnson protocol", position=5.4, impressions=4_400, clicks=286, ctr=0.065, trend="up", difficulty=44, opportunity_score=88),
    KeywordRanking(keyword="lifespan extension", position=28.2, impressions=3_700, clicks=38, ctr=0.010, trend="down", difficulty=67, opportunity_score=51),
]

MOCK_CONTENT_OPPORTUNITIES: list[ContentOpportunity] = [
    ContentOpportunity(keyword="longevity AI assistant", current_position=None, potential_traffic_gain=2_400, competition="low", suggested_content_type="pillar page"),
    ContentOpportunity(keyword="rapamycin longevity", current_position=44.2, potential_traffic_gain=1_800, competition="medium", suggested_content_type="how-to guide"),
    ContentOpportunity(keyword="longevity blood test panel", current_position=38.6, potential_traffic_gain=1_400, competition="low", suggested_content_type="FAQ"),
    ContentOpportunity(keyword="best longevity supplements 2026", current_position=None, potential_traffic_gain=3_200, competition="medium", suggested_content_type="comparison"),
    ContentOpportunity(keyword="Peter Attia longevity protocol", current_position=22.8, potential_traffic_gain=2_100, competition="medium", suggested_content_type="pillar page"),
    ContentOpportunity(keyword="longevity vs lifespan", current_position=None, potential_traffic_gain=900, competition="low", suggested_content_type="FAQ"),
    ContentOpportunity(keyword="metformin anti aging", current_position=51.3, potential_traffic_gain=1_600, competition="high", suggested_content_type="how-to guide"),
    ContentOpportunity(keyword="AI health coaching", current_position=None, potential_traffic_gain=4_100, competition="medium", suggested_content_type="pillar page"),
]

MOCK_TECHNICAL_ISSUES: list[TechnicalIssue] = [
    TechnicalIssue(
        severity="critical", category="speed",
        title="LCP above 4s on mobile",
        description="Largest Contentful Paint averages 4.2s on mobile — Google's threshold for 'poor' is 4s. Likely cause: unoptimized hero images and render-blocking scripts.",
        pages_affected=34, fix_effort="medium", impact="high",
        tool_hint="Audit with Lighthouse (lighthouse https://asklongevity.ai --form-factor=mobile)",
    ),
    TechnicalIssue(
        severity="critical", category="structured_data",
        title="Missing Article schema on blog posts",
        description="87 blog posts lack Article or BlogPosting JSON-LD. This suppresses rich results (byline, date, breadcrumb) in Google Search.",
        pages_affected=87, fix_effort="easy", impact="high",
        tool_hint="Add JSON-LD Article schema; validate with Google Rich Results Test",
    ),
    TechnicalIssue(
        severity="critical", category="crawl",
        title="14 pages returning 404",
        description="crawl4ai found 14 internal links pointing to deleted pages. These waste crawl budget and create dead ends for users.",
        pages_affected=14, fix_effort="easy", impact="high",
        tool_hint="Crawl with crawl4ai to find all broken links, then 301-redirect or fix",
    ),
    TechnicalIssue(
        severity="warning", category="content",
        title="23 pages below 600 words (thin content)",
        description="Pages under 600 words rarely rank for competitive longevity keywords. Consider merging or expanding these stubs.",
        pages_affected=23, fix_effort="hard", impact="medium",
        tool_hint="Use contentswift gap analysis to identify expansion topics",
    ),
    TechnicalIssue(
        severity="warning", category="crawl",
        title="Sitemap not submitted to GSC",
        description="No sitemap.xml submission detected in Google Search Console. GSC cannot efficiently discover new content.",
        pages_affected=1, fix_effort="easy", impact="high",
        tool_hint="Submit via google-indexing-script or GSC UI under Sitemaps",
    ),
    TechnicalIssue(
        severity="warning", category="speed",
        title="No image lazy loading on archive pages",
        description="Category and tag pages load all images eagerly. Add loading='lazy' to improve INP and reduce initial payload.",
        pages_affected=12, fix_effort="easy", impact="medium",
        tool_hint="Check with Lighthouse performance audit",
    ),
    TechnicalIssue(
        severity="warning", category="structured_data",
        title="FAQ schema missing on Q&A pages",
        description="8 longevity FAQ pages lack FAQPage schema. Adding it can unlock FAQ rich results which double visible SERP real estate.",
        pages_affected=8, fix_effort="easy", impact="medium",
        tool_hint="Add FAQPage JSON-LD; validate with Google Rich Results Test",
    ),
    TechnicalIssue(
        severity="info", category="crawl",
        title="robots.txt disallowing /api/ paths",
        description="The /api/ path is blocked in robots.txt. This is fine as it contains no indexable content — worth documenting.",
        pages_affected=0, fix_effort="easy", impact="low",
        tool_hint="Review with crawl4ai robots.txt audit",
    ),
    TechnicalIssue(
        severity="info", category="content",
        title="No canonical tags on paginated category pages",
        description="Category pages beyond page 1 lack rel=canonical, which may cause duplicate content signals.",
        pages_affected=6, fix_effort="easy", impact="low",
        tool_hint="Crawl with crawl4ai to audit canonical tag coverage across all paginated pages",
    ),
]

MOCK_SEO_AUDIT = SEOAuditResult(
    score=61,
    issues=MOCK_TECHNICAL_ISSUES,
    crawled_pages=101,
    crawl_date="2026-04-20",
)
