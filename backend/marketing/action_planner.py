"""
marketing/action_planner.py
────────────────────────────
Prioritized action plan for AskLongevity.ai organic growth.
Toggle state is in-memory — replace with SQLite/Redis for persistence.
"""

from typing import Literal
from pydantic import BaseModel


class ActionItem(BaseModel):
    id: str
    priority: int
    category: Literal[
        "technical_seo", "content", "keywords",
        "indexing", "social", "paid", "community", "backlinks"
    ]
    title: str
    description: str
    estimated_impact: Literal["high", "medium", "low"]
    estimated_effort: Literal["easy", "medium", "hard"]
    time_to_results: str
    tools: list[str]
    status: Literal["todo", "in_progress", "done"]
    quick_win: bool


_ACTION_ITEMS: list[dict] = [
    dict(id="act-01", priority=1, category="indexing",
         title="Submit sitemap + run google-indexing-script for top 50 pages",
         description="Your sitemap is not submitted to Google Search Console. Submit sitemap.xml via GSC, then use google-indexing-script to push top 50 URLs directly to Google's Indexing API for faster discovery. This is the single highest-leverage free action you can take today.",
         estimated_impact="high", estimated_effort="easy", time_to_results="1–3 days",
         tools=["google-indexing-script", "google-searchconsole"], status="todo", quick_win=True),

    dict(id="act-02", priority=2, category="technical_seo",
         title="Fix Core Web Vitals — LCP under 2.5s on mobile",
         description="Lighthouse shows LCP of 4.2s on mobile. Optimize hero images (use WebP, add width/height attributes), defer non-critical JS, and add resource hints. Google uses CWV as a ranking signal. Target: LCP <2.5s, CLS <0.1, INP <200ms.",
         estimated_impact="high", estimated_effort="medium", time_to_results="2–4 weeks",
         tools=["lighthouse"], status="todo", quick_win=False),

    dict(id="act-03", priority=3, category="technical_seo",
         title="Add Article + FAQ JSON-LD schema to all content pages",
         description="87 blog posts and 8 FAQ pages lack structured data. Article schema unlocks rich results with author, date, and breadcrumbs. FAQPage schema doubles your SERP footprint with expanded answers. Write a script to generate and inject JSON-LD across all pages.",
         estimated_impact="high", estimated_effort="easy", time_to_results="1–2 weeks",
         tools=["crawl4ai"], status="todo", quick_win=True),

    dict(id="act-04", priority=4, category="technical_seo",
         title="Crawl site with crawl4ai — fix 14 broken internal links",
         description="crawl4ai found 14 internal 404 links wasting crawl budget. Export the broken link report, create 301 redirects or update links to live pages. Also audit for redirect chains over 2 hops.",
         estimated_impact="high", estimated_effort="medium", time_to_results="3–5 days",
         tools=["crawl4ai"], status="todo", quick_win=False),

    dict(id="act-05", priority=5, category="keywords",
         title="GSC CTR optimization — rewrite title tags for 15 low-CTR pages",
         description="Filter GSC for pages with >500 impressions and <3% CTR. These pages rank but don't get clicked. Rewrite title tags to include the exact keyword at the front, add a number or year, and add emotional hooks (e.g. 'The 2026 Guide to...'). Expected CTR lift: 40–80%.",
         estimated_impact="high", estimated_effort="easy", time_to_results="2–4 weeks",
         tools=["google-searchconsole"], status="todo", quick_win=True),

    dict(id="act-06", priority=6, category="content",
         title="Build 10 longevity pillar pages (keyword clusters)",
         description="Create comprehensive 3,000+ word pillar pages: NAD+ biology, Bryan Johnson protocol deep-dive, longevity supplements guide, healthspan vs lifespan, biohacking beginner guide, longevity diet comparison, anti-aging science overview, AI health coaching, longevity blood biomarkers, and rapamycin research. Each pillar links to 5–8 supporting posts.",
         estimated_impact="high", estimated_effort="medium", time_to_results="2–3 months",
         tools=["contentswift", "crawl4ai"], status="todo", quick_win=False),

    dict(id="act-07", priority=7, category="keywords",
         title="Target long-tail 'longevity + [topic]' keyword clusters",
         description="Use SerpBear to track and identify long-tail opportunities: 'longevity supplements for women over 50', 'NAD+ dosage calculator', 'longevity AI chatbot', 'how long will I live calculator'. These have low difficulty (20–40) and high conversion intent. Target 20 new long-tails per month.",
         estimated_impact="high", estimated_effort="medium", time_to_results="6–10 weeks",
         tools=["serpbear", "contentswift"], status="todo", quick_win=False),

    dict(id="act-08", priority=8, category="content",
         title="Run contentswift gap analysis vs top 10 longevity sites",
         description="Use contentswift to compare AskLongevity.ai content against longevity.technology, lifespan.io, and Peter Attia's Drive. Identify topics they rank for that you don't cover. Prioritize gaps with high traffic + low competition.",
         estimated_impact="medium", estimated_effort="easy", time_to_results="1–2 weeks",
         tools=["contentswift"], status="todo", quick_win=True),

    dict(id="act-09", priority=9, category="community",
         title="Join and post in 5 longevity Discord communities daily",
         description="Identify top longevity/biohacking Discord servers (Huberman Lab, Levels Health, Bryan Johnson Discord, r/longevity). Post helpful, non-promotional answers to questions. Add site link in profile bio. Target: 1 valuable post per server per day. Drives high-intent referral traffic.",
         estimated_impact="medium", estimated_effort="easy", time_to_results="2–4 weeks",
         tools=[], status="todo", quick_win=True),

    dict(id="act-10", priority=10, category="social",
         title="Set up automated X/Twitter content sharing pipeline",
         description="Use Twitter API v2 to auto-post new blog articles as threads. Format: hook tweet → 4–5 key points → CTA to full article. Schedule for 8am PST (peak longevity community engagement). Create a GitHub Action that triggers on new RSS feed items.",
         estimated_impact="medium", estimated_effort="medium", time_to_results="2–3 weeks",
         tools=[], status="todo", quick_win=False),

    dict(id="act-11", priority=11, category="paid",
         title="Meta retargeting campaign — site visitors, $50/day",
         description="Create a Meta Custom Audience from site visitors (pixel must be installed first). Run retargeting ads to visitors who read 2+ pages but didn't sign up. Use social proof creative: 'Join 1,800+ longevity researchers on AskLongevity.ai'. Budget: $50/day. Expected: CPC $0.40–0.80, conversion rate 4–8%.",
         estimated_impact="medium", estimated_effort="hard", time_to_results="2–4 weeks",
         tools=[], status="todo", quick_win=False),

    dict(id="act-12", priority=12, category="content",
         title="Launch weekly longevity newsletter to build email list",
         description="Create a weekly digest of longevity research, AI health news, and AskLongevity.ai insights. Offer a lead magnet (e.g. 'The 2026 Longevity Supplement Stack' PDF). Use email as a direct channel to drive repeat visits and reduce Google dependency. Target: 100 subscribers in month 1.",
         estimated_impact="medium", estimated_effort="medium", time_to_results="1–3 months",
         tools=[], status="todo", quick_win=False),

    dict(id="act-13", priority=13, category="backlinks",
         title="HARO/Qwoted outreach — 3 longevity expert quotes per week",
         description="Monitor HARO and Qwoted for longevity, health, AI, and aging queries. Respond with expert commentary citing AskLongevity.ai as the source. Target publications: Healthline, Medical News Today, Wired, TechCrunch Health. Goal: 3 quality backlinks/month from DA40+ sites.",
         estimated_impact="low", estimated_effort="hard", time_to_results="2–4 months",
         tools=[], status="todo", quick_win=False),

    dict(id="act-14", priority=14, category="paid",
         title="Google Ads — brand + category keywords ($10/day to start)",
         description="Run a Brand campaign (protect 'AskLongevity' branded searches) + a small Category campaign targeting 'longevity AI' and 'health AI assistant'. Start at $10/day, measure 2 weeks, scale if CPA <$8. Use RSAs with longevity-specific CTAs.",
         estimated_impact="low", estimated_effort="hard", time_to_results="4–8 weeks",
         tools=[], status="todo", quick_win=False),

    dict(id="act-15", priority=15, category="keywords",
         title="Set up SerpBear for self-hosted rank tracking",
         description="Deploy SerpBear (self-hosted, free) to track 50 target longevity keywords daily. Connect to Google Search Console for impression data. This replaces expensive rank tracking SaaS and feeds data directly into this marketing dashboard.",
         estimated_impact="low", estimated_effort="easy", time_to_results="1–2 days",
         tools=["serpbear"], status="todo", quick_win=True),
]


def get_all_items() -> list[ActionItem]:
    return [ActionItem(**item) for item in _ACTION_ITEMS]


def toggle_item(item_id: str) -> ActionItem | None:
    for item in _ACTION_ITEMS:
        if item["id"] == item_id:
            item["status"] = "done" if item["status"] == "todo" else "todo"
            return ActionItem(**item)
    return None
