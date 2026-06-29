# T8 — Orchestrator: State + Errors + Router

**Status:** `pending`
**Depends on:** T3

## Goal
LangGraph `CycleState` TypedDict, all custom error types, and the conditional edge routing function.

## Files to Create

```
orchestrator/state.py
orchestrator/errors.py
orchestrator/router.py
```

## `orchestrator/state.py`

```python
from typing import TypedDict

class CycleState(TypedDict):
    cycle_id: str
    profile: dict | None
    search_criteria: dict | None
    raw_opportunities: list[dict]
    scored_opportunities: list[dict]
    shortlisted: list[dict]
    rejected: list[dict]
    report_path: str | None
    errors: list[str]
    token_spend: float
    sources_queried: list[str]
```

All values are plain dicts (serialised Pydantic models) — LangGraph checkpointer requires JSON-serialisable state.

## `orchestrator/errors.py`

```python
class SourceBlockedError(Exception): ...        # source policy = blocked
class RateLimitExceededError(Exception): ...    # source request cap exceeded
class BudgetExceededError(Exception): ...       # token spend > config limit
class SchemaValidationError(Exception): ...     # agent output failed Pydantic parse
class LLMTimeoutError(Exception): ...           # LLM call timed out
class ProfileNotFoundError(Exception): ...      # no active profile in MongoDB
```

Rule: all errors caught and handled in orchestrator nodes only — never inside agents or sources.

## `orchestrator/router.py`

```python
def route_after_profile(state: CycleState) -> str:
    return "profile_exists" if state["profile"] is not None else "no_profile"
```

## Steps

1. Write `orchestrator/state.py`
2. Write `orchestrator/errors.py`
3. Write `orchestrator/router.py`
4. Run `mypy orchestrator/state.py orchestrator/errors.py orchestrator/router.py` — must pass
5. Commit
