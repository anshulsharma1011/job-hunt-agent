from orchestrator.router import route_after_profile
from orchestrator.state import CycleState


def _state(**overrides: object) -> CycleState:
    base: CycleState = {
        "cycle_id": "test-cycle",
        "profile": None,
        "search_criteria": None,
        "raw_opportunities": [],
        "scored_opportunities": [],
        "shortlisted": [],
        "rejected": [],
        "report_path": None,
        "errors": [],
        "token_spend": 0.0,
        "sources_queried": [],
    }
    return {**base, **overrides}  # type: ignore[return-value]


def test_routes_to_no_profile_when_profile_is_none() -> None:
    assert route_after_profile(_state(profile=None)) == "no_profile"


def test_routes_to_profile_exists_when_profile_present() -> None:
    state = _state(profile={"name": "Anshul", "skills": ["Python"]})
    assert route_after_profile(state) == "profile_exists"


def test_routes_to_profile_exists_when_profile_is_empty_dict() -> None:
    assert route_after_profile(_state(profile={})) == "profile_exists"
