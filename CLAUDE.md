# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent AI orchestration system for managing advertising campaigns across Meta, Google, and LinkedIn. Designed for local SMBs with weak audience targeting as the core pain point. The system uses 8 specialized agents coordinated by a central Orchestrator with token budget enforcement.

## Project Structure

```
backend/                    # Python backend (FastAPI + agent pipeline)
  core/                     # Shared types, budget manager, orchestrator, LLM/API clients
  agents/                   # 8 specialist agents + registry
  api/                      # FastAPI routes
  tests/                    # pytest test suite
  main.py                   # Entry point (server or CLI)
  requirements.txt
frontend/                   # React dashboard (Vite)
  src/components/           # Dashboard, AgentNetwork, CostEstimator
  src/api/client.js         # API client for backend
```

Root-level files (`orchestrator.py`, `budget_manager.py`, `main (1).py`, etc.) are the original scaffolds — superseded by `backend/`.

## Commands

```bash
# Backend — start FastAPI server (serves API on :8000)
cd backend && pip install -r requirements.txt && python main.py

# Backend — CLI pipeline run
cd backend && python main.py --cli
cd backend && python main.py --cli --complexity high
cd backend && python main.py --cli --dry-run

# Backend — run tests
cd backend && python -m pytest tests/ -v

# Backend — run a single test
cd backend && python -m pytest tests/ -v -k "test_complete_result_advances"

# Frontend — dev server (proxies /api to :8000)
cd frontend && npm install && npm run dev

# Frontend — production build
cd frontend && npm run build
```

## Architecture

### Agent Network (8 agents, 4 layers)

```
Command Layer:      Orchestrator (Claude Sonnet 4.5)
Intelligence Layer: Audience Intel (Claude Sonnet 4.5), Analytics (GPT-5)
Platform Layer:     Meta Ads (GPT-5), Google Ads (GPT-5), LinkedIn Ads (GPT-5), Creative (Gemini 3 Pro)
Output Layer:       Reporting (Claude Haiku 4.5)
```

### Two Agent Modes

The registry (`agents/registry.py`) supports two modes via `build_agent_registry(use_llm=)`:
- **Simulation mode** (default when no API keys): `specialist_agents.py` — mock data, fast, for testing
- **LLM mode** (auto-enabled when ANTHROPIC_API_KEY or OPENAI_API_KEY is set): `audience_intel_agent.py` + `analytics_agent.py` — real Claude/GPT calls, HubSpot CRM, GA4 data

Only Audience Intel and Analytics have LLM-backed implementations. The other 6 agents always run simulation mode regardless of API key presence.

### Pipeline Flow (6 steps in `core/orchestrator.py`)

1. **Orchestrator decomposes** goal into sub-tasks
2. **Audience Intel + Analytics** run in parallel (`asyncio.gather`)
3. Gate: if Audience Intel coverage < 50%, pipeline stops
4. **Platform agents + Creative** run in parallel, consuming audience + analytics data
5. **Orchestrator aggregates** all results
6. **Reporting** generates digest

### Decision Tree (`Orchestrator.decide`)

| Status | Coverage | Action |
|--------|----------|--------|
| COMPLETE | — | ADVANCE |
| PARTIAL_SAFE | >= 80% | CONTINUE_WITH_WARNING |
| PARTIAL_SAFE | 50–79% + checkpoint | RETRY_FROM_CHECKPOINT |
| PARTIAL_SAFE | 50–79% no checkpoint | RETRY_FROM_SCRATCH |
| PARTIAL_SAFE | < 50% | REPLAN |
| PARTIAL_UNSAFE | — | RETRY_FROM_SCRATCH (data discarded) |
| BUDGET_EXCEEDED | + checkpoint | RETRY_FROM_CHECKPOINT |
| BUDGET_EXCEEDED | no checkpoint | ESCALATE_TO_HUMAN |
| FAILED | retries < 2 | RETRY_FROM_SCRATCH |
| FAILED | retries >= 2 | ESCALATE_TO_HUMAN |

Coverage thresholds are tunable via `COVERAGE_THRESHOLDS` dict in `orchestrator.py`.

### Token Budget System

- Budgets assigned BEFORE agent starts, never mid-run
- Agents call `check_budget()` at the START of each work unit, never mid-calculation
- Complexity multipliers: LOW=0.65x, NORMAL=1.0x, HIGH=1.45x
- Retry expansion: checkpoint=1.4x, full=1.6x, compounded per retry
- Safety margin: 15% reserved buffer
- `TokenBudgetManager` tracks actual usage for auto-tuning

### Core Types (`core/models.py`)

All shared enums and dataclasses live here — this is the authoritative type reference:
- `CompletionStatus` — COMPLETE, PARTIAL_SAFE, PARTIAL_UNSAFE, BUDGET_EXCEEDED, FAILED
- `TaskComplexity` — LOW, NORMAL, HIGH
- `OrchestratorAction` — ADVANCE, CONTINUE_WITH_WARNING, RETRY_FROM_CHECKPOINT, RETRY_FROM_SCRATCH, REPLAN, ESCALATE_TO_HUMAN
- `TokenBudget` — assigned before agent starts; `is_safe_to_start_unit()` called before each work unit
- `AgentResult` — every agent returns this; coverage = `items_processed / items_total`
- `PipelineState` — tracks a full run (run_id, per-agent results + decisions, warnings, elapsed time)

### BaseAgent (`agents/base_agent.py`)

All agents extend this abstract class. Key methods:
- `check_budget(budget, estimated_unit_cost)` → bool — call before each work unit
- `make_result(status, data, items_processed, items_total, checkpoint, error)` → AgentResult
- `simulate_token_usage(base, variance)` — for mock/simulation agents

### Design Rules

1. PARTIAL_UNSAFE data is **always discarded** — never passed downstream
2. Retry counts capped at 2 per agent — escalate to human instead of infinite loops
3. Agents return `AgentResult` with declared completeness — no silent partial returns
4. The ROAS join in `AnalyticsAgent` is atomic — returns PARTIAL_UNSAFE if budget runs out mid-calculation
5. Agents save checkpoints at work-unit boundaries (e.g., after each segment) to enable RETRY_FROM_CHECKPOINT

### External Service Clients (`core/`)

- `llm_client.py` — Routes to Anthropic/OpenAI/Google based on agent's model. Falls back to mock responses when API keys are missing.
- `hubspot_client.py` — HubSpot CRM segments. Falls back to 5 mock SMB segments.
- `ga4_client.py` — GA4 conversion data. Falls back to mock campaign records.

### Environment Variables (optional — system works without them via mocks)

```
ANTHROPIC_API_KEY     — Enables real Claude calls for Orchestrator, Audience Intel
OPENAI_API_KEY        — Enables real GPT calls for Analytics, platform agents
GOOGLE_API_KEY        — Enables real Gemini calls for Creative agent
HUBSPOT_API_KEY       — Enables real HubSpot CRM data
GA4_PROPERTY_ID       — Enables real GA4 conversion data
GOOGLE_APPLICATION_CREDENTIALS — Path to GA4 service account JSON
```

### API Endpoints (`backend/api/routes.py`)

- `GET  /api/health` — Health check
- `GET  /api/agents` — List agents with models, budgets, pricing
- `POST /api/pipeline/run` — Run full pipeline (body: `{goal, complexity}`)
- `POST /api/pipeline/dry-run` — Cost estimate without execution (body: `{complexity}`)
- `GET  /api/pipeline/status/{run_id}` — Pipeline run status

In-flight and completed runs are stored in `_pipeline_runs` dict (in-process, not persisted).

### Frontend Components

- **Dashboard** — Pipeline runner form, polls `/api/pipeline/status/{runId}` every 2s, shows per-agent results table
- **AgentNetwork** — Static visualization of the 4-layer architecture with color-coded layers
- **CostEstimator** — Complexity selector that calls dry-run endpoint and shows per-agent token/USD breakdown

### Tests

`backend/tests/test_orchestrator.py` contains full coverage of all decision-tree paths in `TestOrchestratorDecisionTree`. `conftest.py` provides `make_result(status, processed, total, checkpoint, error, agent_id)` as a test helper to construct `AgentResult` fixtures without touching agent internals.

No linting config is set up (no pyproject.toml, .flake8, or ESLint config).