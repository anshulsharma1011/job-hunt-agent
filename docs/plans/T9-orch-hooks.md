# T9 — Orchestrator: Hooks

**Status:** `pending`
**Depends on:** T4, T7, T8

## Goal
All hook functions in `orchestrator/hooks.py`. Called explicitly from node functions — never from inside agents or sources.

## Files to Create

```
orchestrator/hooks.py
tests/orchestrator/test_hooks.py
```

## `orchestrator/hooks.py`

```python
def apply_source_policy(source_name: str, config: AppConfig) -> None:
    """Raises SourceBlockedError if source policy == 'blocked'."""

def apply_rate_limit(
    source_name: str, request_count: int, config: AppConfig
) -> None:
    """Raises RateLimitExceededError if request_count exceeds config max."""

def apply_dedup(
    raw: list[RawOpportunity],
    opportunity_repo: OpportunityRepository,
) -> list[RawOpportunity]:
    """Returns only opportunities whose external_id is not in MongoDB."""

def validate_output_schema(data: dict, model: type[BaseModel]) -> BaseModel:
    """Parses data into model. Raises SchemaValidationError on failure."""

def apply_budget_gate(current_spend: float, config: AppConfig) -> None:
    """Raises BudgetExceededError if current_spend >= token_budget_per_cycle."""
```

## Tests — Adversarial Inputs Required

```
tests/orchestrator/test_hooks.py

apply_source_policy:
  - test_allowed_source_does_not_raise
  - test_blocked_source_raises_source_blocked_error
  - test_human_assisted_source_does_not_raise    # only fetch() raises, not policy check

apply_rate_limit:
  - test_within_limit_does_not_raise
  - test_at_limit_raises_rate_limit_exceeded_error
  - test_above_limit_raises_rate_limit_exceeded_error

apply_dedup:
  - test_all_new_opportunities_returned
  - test_all_known_opportunities_dropped          # adversarial: all IDs already in DB
  - test_partial_dedup_returns_only_new

validate_output_schema:
  - test_valid_data_returns_model_instance
  - test_missing_required_field_raises_schema_validation_error
  - test_wrong_type_raises_schema_validation_error

apply_budget_gate:
  - test_under_budget_does_not_raise
  - test_exactly_at_budget_raises_budget_exceeded_error
  - test_over_budget_raises_budget_exceeded_error
```

## Steps

1. Write all 5 hook functions
2. Write adversarial tests — every edge case above must have a test
3. Run `pytest tests/orchestrator/test_hooks.py` — must pass
4. Run `mypy orchestrator/hooks.py` — must pass
5. Commit
