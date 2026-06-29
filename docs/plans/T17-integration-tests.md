# T17 — Integration Tests: Repositories

**Status:** `pending`
**Depends on:** T4

## Goal
Repository tests against real local MongoDB (`test_job_hunt_db`). No mocking at the DB layer.

## Files to Create

```
tests/store/conftest.py
tests/store/test_profile_repo.py
tests/store/test_opportunity_repo.py
tests/store/test_cycle_repo.py
```

## `tests/store/conftest.py`

```python
import pytest
from store.db import get_client, get_db

@pytest.fixture
def test_db(test_config):
    db = get_db(test_config.mongodb)    # connects to test_job_hunt_db
    yield db
    # teardown: drop all test collections after each test
    for collection in db.list_collection_names():
        db.drop_collection(collection)
```

## `tests/store/test_profile_repo.py`

```
- test_save_and_get_active
    → save a profile, get_active() returns it

- test_save_deactivates_previous
    → save v1, save v2, get_active() returns v2 with is_active=True
    → v1 has is_active=False in DB

- test_get_active_returns_none_when_empty
    → empty DB, get_active() returns None

- test_deactivate_all_marks_all_inactive
```

## `tests/store/test_opportunity_repo.py`

```
- test_upsert_many_inserts_new_opportunities
- test_upsert_many_is_idempotent
    → upsert same list twice, count stays the same

- test_get_known_external_ids_returns_correct_set
- test_get_by_cycle_returns_only_that_cycle
```

## `tests/store/test_cycle_repo.py`

```
- test_create_and_get_latest
- test_get_latest_returns_most_recent
    → create two cycles, get_latest() returns the newer one

- test_update_partial_fields
    → create cycle, update only completed_at, other fields unchanged

- test_get_latest_returns_none_when_empty
```

## Steps

1. Write `conftest.py` with teardown fixture
2. Write all three test files
3. Start MongoDB locally (`brew services start mongodb-community`)
4. Run `pytest tests/store/ -v` — all must pass
5. Verify test DB is clean after run: `mongosh test_job_hunt_db --eval "db.getCollectionNames()"`
6. Commit
