# T4 — Store: DB + Repositories

**Status:** `pending`
**Depends on:** T3

## Goal
MongoDB connection singleton and three repository classes. All DB access in the system flows through these — no collection calls outside this layer.

## Files to Create

```
store/db.py
store/repositories/profile_repo.py
store/repositories/opportunity_repo.py
store/repositories/cycle_repo.py
tests/store/conftest.py
tests/store/test_profile_repo.py
tests/store/test_opportunity_repo.py
tests/store/test_cycle_repo.py
```

## `store/db.py`

```python
PROFILES     = "profiles"
OPPORTUNITIES = "opportunities"
CYCLES       = "cycles"
CHECKPOINTS  = "checkpoints"

def get_client(config: MongoConfig) -> MongoClient: ...   # singleton
def get_db(config: MongoConfig) -> Database: ...
```

## Repository Interfaces

**`ProfileRepository`**
```python
def __init__(self, db: Database)
def get_active(self) -> ProfileDoc | None
def save(self, profile: ProfileDoc) -> None       # deactivates all, then inserts
def deactivate_all(self) -> None
```

**`OpportunityRepository`**
```python
def __init__(self, db: Database)
def get_known_external_ids(self, source: str) -> set[str]
def upsert_many(self, opportunities: list[ScoredOpportunity]) -> None
def get_by_cycle(self, cycle_id: str) -> list[ScoredOpportunity]
```

**`CycleRepository`**
```python
def __init__(self, db: Database)
def create(self, cycle: CycleRecord) -> None
def update(self, cycle_id: str, updates: dict) -> None
def get_latest(self) -> CycleRecord | None
```

## Tests

Tests hit real MongoDB — `test_job_hunt_db`. No mocking at the DB layer.

**`tests/store/conftest.py`**
```python
@pytest.fixture
def test_db():
    # connects to test_job_hunt_db
    # drops all collections after each test
```

**`tests/store/test_profile_repo.py`**
```
- test_save_and_get_active
- test_save_deactivates_previous
- test_get_active_returns_none_when_empty
```

**`tests/store/test_opportunity_repo.py`**
```
- test_upsert_many_and_get_by_cycle
- test_get_known_external_ids_returns_correct_set
- test_upsert_many_is_idempotent
```

**`tests/store/test_cycle_repo.py`**
```
- test_create_and_get_latest
- test_update_partial_fields
- test_get_latest_returns_none_when_empty
```

## Steps

1. Write `store/db.py` with collection constants and connection helpers
2. Write `ProfileRepository` — `deactivate_all()` sets `is_active: false` on all docs before insert
3. Write `OpportunityRepository` — `upsert_many()` uses `replace_one(upsert=True)` keyed on `opportunity_id`
4. Write `CycleRepository`
5. Write `conftest.py` with teardown fixture
6. Write all repository tests
7. Run `pytest tests/store/` with MongoDB running — must pass
8. Commit
