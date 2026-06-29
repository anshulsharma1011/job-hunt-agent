from datetime import UTC, datetime

from store.cycle_record import CycleRecord
from store.repositories.cycle_repo import CycleRepository


def _make_cycle(cycle_id: str = "cycle_abc") -> CycleRecord:
    return CycleRecord(
        cycle_id=cycle_id,
        started_at=datetime.now(UTC),
        sources_queried=["greenhouse"],
        discovered_count=10,
        shortlisted_count=3,
        rejected_count=7,
        model_used="ollama/llama3.1:8b",
    )


def test_create_and_get_latest(test_db):
    repo = CycleRepository(test_db)
    cycle = _make_cycle()
    repo.create(cycle)
    latest = repo.get_latest()
    assert latest is not None
    assert latest.cycle_id == "cycle_abc"
    assert latest.discovered_count == 10


def test_update_partial_fields(test_db):
    repo = CycleRepository(test_db)
    repo.create(_make_cycle())
    repo.update("cycle_abc", {"shortlisted_count": 99, "model_used": "updated-model"})
    latest = repo.get_latest()
    assert latest is not None
    assert latest.shortlisted_count == 99
    assert latest.model_used == "updated-model"


def test_get_latest_returns_none_when_empty(test_db):
    repo = CycleRepository(test_db)
    assert repo.get_latest() is None
