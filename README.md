# Ads Agent Network — Budget-Safe Orchestrator Scaffold

## Project Structure
```
ads_agent_network/
├── core/
│   ├── types.py           # All shared types (AgentResult, TokenBudget, etc.)
│   ├── budget_manager.py  # Assigns + tracks token budgets per agent
│   └── orchestrator.py    # Decision engine — evaluates every agent result
├── agents/
│   ├── base_agent.py           # BaseAgent — all agents extend this
│   ├── audience_intel_agent.py # Full checkpoint pattern example
│   └── analytics_agent.py     # PARTIAL_UNSAFE detection example
├── tests/
│   └── test_orchestrator.py   # 17 tests covering every scenario
└── main.py                    # Demo runner with 4 scenarios
```

## Run It
```bash
# Normal run
python main.py --scenario normal

# Budget runs out mid-analysis → partial_safe → auto-retry from checkpoint
python main.py --scenario tight

# Analytics stops mid-join → partial_unsafe → discard + retry from scratch
python main.py --scenario unsafe

# Run all tests
python -m pytest tests/ -v
```

## Key Design Rules
1. Budget assigned BEFORE agent starts — not checked after
2. Agents stop at unit boundaries (segment, turn) — never mid-calculation
3. Every result has an explicit CompletionStatus — no silent partial returns
4. PARTIAL_UNSAFE data is always discarded — never passed downstream
5. Retry counts are capped — no infinite loops, escalate to human instead
