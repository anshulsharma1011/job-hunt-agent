from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agents.reporter_agent import ReporterAgent
from store.lifecycle_event import LifecycleEvent
from store.lifecycle_state import LifecycleState
from store.raw_opportunity import RawOpportunity
from store.recommended_track import RecommendedTrack
from store.scored_opportunity import ScoredOpportunity


def _make_scored_opp(
    external_id: str = "ext-001",
    score: int = 85,
    track: RecommendedTrack = RecommendedTrack.apply,
) -> ScoredOpportunity:
    return ScoredOpportunity(
        opportunity_id=f"opp_{external_id}",
        cycle_id="cycle-test",
        raw=RawOpportunity(
            source="greenhouse",
            source_url=f"https://boards.greenhouse.io/{external_id}",
            external_id=external_id,
            company="Acme Corp",
            role_title="Senior Backend Engineer",
            location="Bangalore / Remote",
            description_raw="Build things.",
        ),
        score=score,
        fit_rationale=["Python match", "Distributed systems experience"],
        red_flags=["Requires 10+ years"],
        recommended_track=track,
        lifecycle_state=LifecycleState.scored,
        history=[LifecycleEvent(state=LifecycleState.scored)],
    )


def _make_state(
    cycle_id: str = "cycle-test",
    shortlisted: list[dict[str, object]] | None = None,
    rejected: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    opp = _make_scored_opp()
    return {
        "cycle_id": cycle_id,
        "profile": None,
        "search_criteria": None,
        "raw_opportunities": [opp.model_dump()],
        "scored_opportunities": [],
        "shortlisted": shortlisted if shortlisted is not None else [opp.model_dump()],
        "rejected": rejected if rejected is not None else [],
        "token_spend": 0.0,
        "sources_queried": ["greenhouse", "indeed"],
        "errors": [],
        "report_path": None,
    }


def _make_config(report_dir: str, threshold: int = 70) -> MagicMock:
    config = MagicMock()
    config.output.report_dir = report_dir
    config.llm.model = "ollama/llama3.1:8b"
    config.matching.score_threshold = threshold
    return config


@pytest.fixture
def agent() -> ReporterAgent:
    return ReporterAgent()


def test_run_creates_report_file(agent: ReporterAgent, tmp_path: Path) -> None:
    state = _make_state()
    config = _make_config(str(tmp_path))

    result = agent.run(state, config)  # type: ignore[arg-type]

    assert "report_path" in result
    report_path = Path(str(result["report_path"]))
    assert report_path.exists()
    assert report_path.suffix == ".txt"


def test_report_file_named_with_cycle_id(agent: ReporterAgent, tmp_path: Path) -> None:
    cycle_id = "abc-123-xyz"
    state = _make_state(cycle_id=cycle_id)
    config = _make_config(str(tmp_path))

    result = agent.run(state, config)  # type: ignore[arg-type]

    report_path = Path(str(result["report_path"]))
    assert cycle_id in report_path.name
    assert report_path.name == f"cycle_{cycle_id}_report.txt"


def test_report_contains_shortlisted_roles(agent: ReporterAgent, tmp_path: Path) -> None:
    shortlisted = [
        _make_scored_opp("ext-001", score=90).model_dump(),
        _make_scored_opp("ext-002", score=75).model_dump(),
    ]
    state = _make_state(shortlisted=shortlisted, rejected=[])
    config = _make_config(str(tmp_path))

    result = agent.run(state, config)  # type: ignore[arg-type]
    content = Path(str(result["report_path"])).read_text()

    assert "Senior Backend Engineer" in content
    assert "Acme Corp" in content
    assert "90" in content
    assert "75" in content
    assert "TOP MATCHES" in content


def test_report_contains_summary_counts(agent: ReporterAgent, tmp_path: Path) -> None:
    shortlisted = [_make_scored_opp("ext-001", score=85).model_dump()]
    rejected = [_make_scored_opp("ext-002", score=40).model_dump()]
    state = _make_state(shortlisted=shortlisted, rejected=rejected)
    config = _make_config(str(tmp_path), threshold=70)

    result = agent.run(state, config)  # type: ignore[arg-type]
    content = Path(str(result["report_path"])).read_text()

    assert "Shortlisted : 1" in content
    assert "Rejected    : 1" in content
    assert "score ≥ 70" in content
    assert "greenhouse" in content
    assert "indeed" in content


def test_run_makes_no_llm_or_db_calls(agent: ReporterAgent, tmp_path: Path) -> None:
    state = _make_state()
    config = _make_config(str(tmp_path))

    mock_llm = MagicMock()
    mock_repo = MagicMock()

    agent.run(state, config)  # type: ignore[arg-type]

    mock_llm.complete.assert_not_called()
    mock_llm.complete_json.assert_not_called()
    mock_repo.find.assert_not_called()
    mock_repo.insert_one.assert_not_called()
