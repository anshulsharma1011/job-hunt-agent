from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from store.models import (
    CycleRecord,
    ExperienceEntry,
    LifecycleEvent,
    LifecycleState,
    ProfileDoc,
    RawOpportunity,
    RecommendedTrack,
    ScoredOpportunity,
    SearchCriteria,
)


def _make_profile() -> ProfileDoc:
    return ProfileDoc(
        profile_id="profile_v1",
        version=1,
        created_at=datetime(2026, 6, 29, 10, 0, 0),
        personal={"name": "Anshul Sharma", "email": "a@b.com", "location": "Bangalore"},
        skills=["Python", "Go"],
        experience_years=8.0,
        seniority="senior",
        experience=[
            ExperienceEntry(company="Acme", role="Backend Engineer", years=3.0, highlights=["Built X"])
        ],
        preferences=SearchCriteria(titles=["Backend Engineer"], locations=["Bangalore"], remote=True),
        source_files=["resume_v3.pdf"],
    )


def _make_scored_opportunity() -> ScoredOpportunity:
    raw = RawOpportunity(
        source="greenhouse",
        source_url="https://boards.greenhouse.io/acme/jobs/123",
        external_id="acme-123",
        company="Acme",
        role_title="Senior Backend Engineer",
        location="Bangalore",
        description_raw="We need a Python engineer.",
    )
    return ScoredOpportunity(
        opportunity_id="opp_abc12345",
        cycle_id="cycle_xyz",
        raw=raw,
        score=85,
        fit_rationale=["Strong Python", "Right seniority", "Remote friendly"],
        red_flags=[],
        recommended_track=RecommendedTrack.apply,
        lifecycle_state=LifecycleState.shortlisted,
    )


def test_profile_doc_round_trip():
    profile = _make_profile()
    dumped = profile.model_dump()
    restored = ProfileDoc.model_validate(dumped)
    assert restored == profile


def test_scored_opportunity_round_trip():
    opp = _make_scored_opportunity()
    dumped = opp.model_dump()
    restored = ScoredOpportunity.model_validate(dumped)
    assert restored == opp


def test_cycle_record_round_trip():
    record = CycleRecord(
        cycle_id="cycle_abc123",
        started_at=datetime(2026, 6, 29, 18, 0, 0),
        sources_queried=["greenhouse", "indeed"],
        discovered_count=47,
        shortlisted_count=12,
        rejected_count=35,
        token_spend=0.0,
        model_used="ollama/llama3.1:8b",
    )
    dumped = record.model_dump()
    restored = CycleRecord.model_validate(dumped)
    assert restored == record


def test_invalid_lifecycle_state_raises():
    with pytest.raises(ValidationError):
        LifecycleEvent(state="nonexistent_state", at=datetime.now(UTC))


def test_search_criteria_defaults():
    criteria = SearchCriteria(titles=["SWE"], locations=["Bangalore"], remote=False)
    assert criteria.comp_min_lpa is None
    assert criteria.company_stages == []
    assert criteria.exclusion_keywords == []
    assert criteria.score_threshold == 70
