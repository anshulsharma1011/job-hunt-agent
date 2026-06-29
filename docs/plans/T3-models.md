# T3 — Store: Models

**Status:** `pending`
**Depends on:** T2

## Goal
All Pydantic data models in one file. Every layer imports data shapes from here — nothing defines its own.

## Files to Create

```
store/models.py
tests/store/test_models.py
```

## Models (in definition order)

```python
# Enums
class LifecycleState(str, Enum): ...     # discovered → closed
class RecommendedTrack(str, Enum): ...   # apply | outreach | skip
class SourcePolicy(str, Enum): ...       # allowed | human-assisted | blocked

# Profile
class ExperienceEntry(BaseModel): ...
class SearchCriteria(BaseModel): ...
class ProfileDoc(BaseModel): ...

# Opportunity
class RawOpportunity(BaseModel): ...
class LifecycleEvent(BaseModel): ...
class ScoredOpportunity(BaseModel): ...

# Cycle
class CycleRecord(BaseModel): ...
```

Full field definitions in `docs/LLD.md §2`.

## Tests

```
tests/store/test_models.py
  - test_profile_doc_round_trip          # construct → dump → validate → equal
  - test_scored_opportunity_round_trip
  - test_cycle_record_round_trip
  - test_invalid_lifecycle_state_raises
  - test_search_criteria_defaults
```

## Steps

1. Define enums first
2. Define leaf models (`ExperienceEntry`, `LifecycleEvent`)
3. Define `SearchCriteria`, `ProfileDoc`
4. Define `RawOpportunity`, `ScoredOpportunity`
5. Define `CycleRecord`
6. Write round-trip tests
7. Run `pytest tests/store/test_models.py` — must pass
8. Run `mypy store/models.py` — must pass
9. Commit
