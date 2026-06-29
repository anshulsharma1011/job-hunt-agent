from datetime import UTC, datetime

from store.experience_entry import ExperienceEntry
from store.profile_doc import ProfileDoc
from store.repositories.profile_repo import ProfileRepository
from store.search_criteria import SearchCriteria


def _make_profile(profile_id: str = "profile_v1", version: int = 1) -> ProfileDoc:
    return ProfileDoc(
        profile_id=profile_id,
        version=version,
        created_at=datetime.now(UTC),
        personal={"name": "Anshul", "email": "a@b.com", "location": "Bangalore"},
        skills=["Python"],
        experience_years=8.0,
        seniority="senior",
        experience=[ExperienceEntry(company="Acme", role="SWE", years=3.0, highlights=[])],
        preferences=SearchCriteria(titles=["SWE"], locations=["Bangalore"], remote=True),
        source_files=["resume.pdf"],
    )


def test_save_and_get_active(test_db):
    repo = ProfileRepository(test_db)
    profile = _make_profile()
    repo.save(profile)
    result = repo.get_active()
    assert result is not None
    assert result.profile_id == "profile_v1"
    assert result.is_active is True


def test_save_deactivates_previous(test_db):
    repo = ProfileRepository(test_db)
    repo.save(_make_profile("profile_v1", 1))
    repo.save(_make_profile("profile_v2", 2))
    active = repo.get_active()
    assert active is not None
    assert active.profile_id == "profile_v2"
    all_docs = list(test_db["profiles"].find({"is_active": False}))
    assert len(all_docs) == 1
    assert all_docs[0]["profile_id"] == "profile_v1"


def test_get_active_returns_none_when_empty(test_db):
    repo = ProfileRepository(test_db)
    assert repo.get_active() is None
