"""
api/marketing_routes.py
────────────────────────
FastAPI routes for the Marketing Intelligence Hub.
All endpoints return mock data; integration comments mark real API swap-in points.
"""

from fastapi import APIRouter, HTTPException, Query

from marketing.seo_data import (
    SEOOverview, SEOAuditResult,
    MOCK_SEO_OVERVIEW, MOCK_KEYWORD_RANKINGS,
    MOCK_CONTENT_OPPORTUNITIES, MOCK_SEO_AUDIT,
)
from marketing.channels import ChannelMetrics, MOCK_CHANNELS
from marketing.action_planner import ActionItem, get_all_items, toggle_item
from marketing.budget import BudgetPlan, generate_budget_plan

marketing_router = APIRouter(prefix="/api/marketing")


@marketing_router.get("/seo/overview", response_model=SEOOverview)
async def get_seo_overview():
    # REAL: query GSC API for impressions/clicks/position + Lighthouse for scores
    return MOCK_SEO_OVERVIEW


@marketing_router.get("/seo/keywords")
async def get_seo_keywords():
    # REAL: query SerpBear API (GET /api/keywords) + GSC for CTR data
    return {
        "rankings": [r.model_dump() for r in MOCK_KEYWORD_RANKINGS],
        "opportunities": [o.model_dump() for o in MOCK_CONTENT_OPPORTUNITIES],
    }


@marketing_router.get("/seo/audit", response_model=SEOAuditResult)
async def get_seo_audit():
    # REAL: run crawl4ai CrawlResult pipeline + parse Lighthouse JSON report
    return MOCK_SEO_AUDIT


@marketing_router.get("/channels", response_model=list[ChannelMetrics])
async def get_channels():
    # REAL: aggregate from GSC API, Google Ads API, Meta Marketing API, Twitter API v2
    return MOCK_CHANNELS


@marketing_router.get("/action-plan", response_model=list[ActionItem])
async def get_action_plan():
    return get_all_items()


@marketing_router.get("/budget", response_model=BudgetPlan)
async def get_budget(monthly_budget: float = Query(default=300.0, ge=0, le=50_000)):
    return generate_budget_plan(monthly_budget)


@marketing_router.post("/action-plan/{item_id}/toggle", response_model=ActionItem)
async def toggle_action_item(item_id: str):
    item = toggle_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Action item '{item_id}' not found")
    return item
