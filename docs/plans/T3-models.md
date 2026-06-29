# T3 — Store: Models

**Status:** `pending`
**Depends on:** T2

## Goal
All Pydantic data models in one file. Every layer imports data shapes from here — nothing defines its own.

## Files to Create

One class per file. `store/models.py` re-exports all via `__all__`.

```
store/lifecycle_state.py
store/recommended_track.py
store/source_policy.py
store/experience_entry.py
store/search_criteria.py
store/profile_doc.py
store/raw_opportunity.py
store/lifecycle_event.py
store/scored_opportunity.py
store/cycle_record.py
store/models.py
tests/store/test_models.py
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
