"""
agents/registry.py
──────────────────
Builds the agent registry mapping agent_id -> async callable.
The Orchestrator uses this to dispatch tasks.

Supports two modes:
  - use_llm=True:  LLM-backed agents (real Claude/GPT/Gemini calls)
  - use_llm=False: Simulation agents (mock data, for testing)
"""

from __future__ import annotations

import os
from typing import Callable

from core.models import AgentResult, TokenBudget
from .specialist_agents import (
    OrchestratorAgent,
    AudienceIntelAgent,
    AnalyticsAgent,
    MetaAdsAgent,
    GoogleAdsAgent,
    LinkedInAdsAgent,
    CreativeAgent,
    ReportingAgent,
)
from .audience_intel_agent import AudienceIntelAgentLLM
from .analytics_agent import AnalyticsAgentLLM


def build_agent_registry(use_llm: bool | None = None) -> dict[str, Callable]:
    """
    Build a registry mapping agent_id -> async callable.
    Each callable has signature: (task: dict, budget: TokenBudget) -> AgentResult

    Args:
        use_llm: If True, use LLM-backed agents for audience_intel and analytics.
                 If None, auto-detect based on ANTHROPIC_API_KEY env var.
    """
    if use_llm is None:
        use_llm = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))

    agent_map: dict[str, type] = {
        "orchestrator":   OrchestratorAgent,
        "audience_intel": AudienceIntelAgentLLM if use_llm else AudienceIntelAgent,
        "analytics":      AnalyticsAgentLLM if use_llm else AnalyticsAgent,
        "meta_ads":       MetaAdsAgent,
        "google_ads":     GoogleAdsAgent,
        "linkedin_ads":   LinkedInAdsAgent,
        "creative":       CreativeAgent,
        "reporting":      ReportingAgent,
    }

    registry: dict[str, Callable] = {}

    for agent_id, agent_cls in agent_map.items():
        def make_runner(cls=agent_cls):
            async def runner(task: dict, budget: TokenBudget) -> AgentResult:
                agent = cls()
                return await agent.run(task, budget)
            return runner

        registry[agent_id] = make_runner()

    return registry
