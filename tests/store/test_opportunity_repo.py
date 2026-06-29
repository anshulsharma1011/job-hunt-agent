from datetime import UTC, datetime

from store.lifecycle_state import LifecycleState
from store.raw_opportunity import RawOpportunity
from store.recommended_track import RecommendedTrack
from store.repositories.opportunity_repo import OpportunityRepository
from store.scored_opportunity import ScoredOpportunity


def _make_opp(opportunity_id: str, external_id: str, cycle_id: str = "cycle_abc") -> ScoredOpportunity:
    return ScoredOpportunity(
        opportunity_id=opportunity_id,
        cycle_id=cycle_id,
        raw=RawOpportunity(
            source="greenhouse",
            source_url="https://example.com/jobs/1",
            external_id=external_id,
            company="Acme",
            role_title="Backend Engineer",
            location="Bangalore",
            description_raw="We need a Python engineer.",
            fetched_at=datetime.now(UTC),
        ),
        score=85,
        fit_rationale=["A", "B", "C"],
        red_flags=[],
        recommended_track=RecommendedTrack.apply,
        lifecycle_state=LifecycleState.shortlisted,
    )


def test_upsert_many_and_get_by_cycle(test_db):
    repo = OpportunityRepository(test_db)
    opps = [_make_opp("opp_001", "gh-001"), _make_opp("opp_002", "gh-002")]
    repo.upsert_many(opps)
    result = repo.get_by_cycle("cycle_abc")
    assert len(result) == 2
    ids = {o.opportunity_id for o in result}
    assert ids == {"opp_001", "opp_002"}


def test_get_known_external_ids_returns_correct_set(test_db):
    repo = OpportunityRepository(test_db)
    repo.upsert_many([_make_opp("opp_001", "gh-001"), _make_opp("opp_002", "gh-002")])
    known = repo.get_known_external_ids("greenhouse")
    assert known == {"gh-001", "gh-002"}


def test_upsert_many_is_idempotent(test_db):
    repo = OpportunityRepository(test_db)
    opp = _make_opp("opp_001", "gh-001")
    repo.upsert_many([opp])
    repo.upsert_many([opp])
    result = repo.get_by_cycle("cycle_abc")
    assert len(result) == 1
