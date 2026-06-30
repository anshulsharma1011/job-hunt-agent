from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agents.discovery_match_agent import DiscoveryMatchAgent
from orchestrator.errors import SourceBlockedError
from store.profile_doc import ProfileDoc
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria

_SCORE_JSON = (
    '{"score": 80, "fit_rationale": ["good fit"], "red_flags": [], "recommended_track": "apply"}',
    100,
)
_LOW_SCORE_JSON = (
    '{"score": 50, "fit_rationale": ["weak fit"], "red_flags": ["overqualified"], "recommended_track": "skip"}',
    80,
)


def _make_raw_opp(external_id: str = "ext-001", source: str = "test_source") -> RawOpportunity:
    return RawOpportunity(
        source=source,
        source_url=f"https://example.com/{external_id}",
        external_id=external_id,
        company="Acme",
        role_title="Software Engineer",
        location="Bangalore",
        description_raw="Build things with Python.",
    )


def _make_profile() -> ProfileDoc:
    return ProfileDoc(
        profile_id="p-001",
        version=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_active=True,
        personal={"name": "Ada"},
        skills=["Python", "Go"],
        experience_years=5.0,
        seniority="senior",
        experience=[],
        preferences=SearchCriteria(titles=["SWE"], locations=["Bangalore"], remote=True),
        source_files=[],
    )


def _make_config(threshold: int = 70, max_per_cycle: int = 10, max_workers: int = 2) -> MagicMock:
    config = MagicMock()
    config.matching.score_threshold = threshold
    config.matching.max_per_cycle = max_per_cycle
    config.matching.max_concurrent_scoring = max_workers
    return config


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.complete.return_value = _SCORE_JSON
    return llm


@pytest.fixture
def mock_source() -> MagicMock:
    source = MagicMock()
    source.name = "test_source"
    source.policy = "allowed"
    source.fetch.return_value = [_make_raw_opp("ext-001"), _make_raw_opp("ext-002")]
    return source


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_known_external_ids.return_value = set()
    return repo


def test_run_returns_shortlisted_and_rejected(
    mock_llm: MagicMock, mock_source: MagicMock, mock_repo: MagicMock
) -> None:
    mock_llm.complete.side_effect = [_SCORE_JSON, _LOW_SCORE_JSON]
    agent = DiscoveryMatchAgent(llm=mock_llm, sources=[mock_source], config=_make_config(threshold=70))

    result: dict[str, Any] = agent.run(
        criteria=SearchCriteria(titles=["SWE"], locations=["BLR"], remote=True),
        profile=_make_profile(),
        opportunity_repo=mock_repo,
        cycle_id="cycle-001",
    )

    assert len(result["raw_opportunities"]) == 2
    assert len(result["shortlisted"]) == 1
    assert len(result["rejected"]) == 1
    assert result["token_spend"] == 180.0
    assert result["sources_queried"] == ["test_source"]


def test_fetch_all_respects_max_per_cycle(
    mock_llm: MagicMock, mock_source: MagicMock, mock_repo: MagicMock
) -> None:
    mock_source.fetch.return_value = [
        _make_raw_opp(f"ext-{i:03d}") for i in range(5)
    ]
    agent = DiscoveryMatchAgent(
        llm=mock_llm, sources=[mock_source], config=_make_config(max_per_cycle=2)
    )

    result: dict[str, Any] = agent.run(
        criteria=SearchCriteria(titles=["SWE"], locations=["BLR"], remote=True),
        profile=_make_profile(),
        opportunity_repo=mock_repo,
        cycle_id="cycle-001",
    )

    assert len(result["raw_opportunities"]) == 2
    assert mock_llm.complete.call_count == 2


def test_dedup_called_before_scoring(
    mock_llm: MagicMock, mock_source: MagicMock, mock_repo: MagicMock
) -> None:
    mock_source.fetch.return_value = [_make_raw_opp("ext-001"), _make_raw_opp("ext-002")]
    mock_repo.get_known_external_ids.return_value = {"ext-001"}
    agent = DiscoveryMatchAgent(llm=mock_llm, sources=[mock_source], config=_make_config())

    result: dict[str, Any] = agent.run(
        criteria=SearchCriteria(titles=["SWE"], locations=["BLR"], remote=True),
        profile=_make_profile(),
        opportunity_repo=mock_repo,
        cycle_id="cycle-001",
    )

    assert mock_llm.complete.call_count == 1
    assert len(result["raw_opportunities"]) == 2


def test_score_batch_scores_all_opps_concurrently(
    mock_llm: MagicMock, mock_source: MagicMock, mock_repo: MagicMock
) -> None:
    mock_source.fetch.return_value = [
        _make_raw_opp("ext-001"),
        _make_raw_opp("ext-002"),
        _make_raw_opp("ext-003"),
    ]
    agent = DiscoveryMatchAgent(
        llm=mock_llm, sources=[mock_source], config=_make_config(max_workers=3)
    )

    result: dict[str, Any] = agent.run(
        criteria=SearchCriteria(titles=["SWE"], locations=["BLR"], remote=True),
        profile=_make_profile(),
        opportunity_repo=mock_repo,
        cycle_id="cycle-001",
    )

    assert mock_llm.complete.call_count == 3
    total_scored = len(result["shortlisted"]) + len(result["rejected"])
    assert total_scored == 3


def test_score_below_threshold_goes_to_rejected(
    mock_llm: MagicMock, mock_source: MagicMock, mock_repo: MagicMock
) -> None:
    mock_llm.complete.return_value = _LOW_SCORE_JSON
    mock_source.fetch.return_value = [_make_raw_opp("ext-001")]
    agent = DiscoveryMatchAgent(
        llm=mock_llm, sources=[mock_source], config=_make_config(threshold=70)
    )

    result: dict[str, Any] = agent.run(
        criteria=SearchCriteria(titles=["SWE"], locations=["BLR"], remote=True),
        profile=_make_profile(),
        opportunity_repo=mock_repo,
        cycle_id="cycle-001",
    )

    assert len(result["shortlisted"]) == 0
    assert len(result["rejected"]) == 1
    assert result["rejected"][0]["score"] == 50


def test_source_policy_applied_per_source(
    mock_llm: MagicMock, mock_repo: MagicMock
) -> None:
    allowed = MagicMock()
    allowed.name = "greenhouse"
    allowed.fetch.return_value = [_make_raw_opp("ext-001", source="greenhouse")]

    blocked = MagicMock()
    blocked.name = "naukri"
    blocked.fetch.return_value = [_make_raw_opp("ext-002", source="naukri")]

    agent = DiscoveryMatchAgent(
        llm=mock_llm, sources=[allowed, blocked], config=_make_config()
    )

    def _fake_policy(source_name: str, _config: object) -> None:
        if source_name == "naukri":
            raise SourceBlockedError("naukri is blocked")

    with patch("agents.discovery_match_agent.apply_source_policy", side_effect=_fake_policy):
        result: dict[str, Any] = agent.run(
            criteria=SearchCriteria(titles=["SWE"], locations=["BLR"], remote=True),
            profile=_make_profile(),
            opportunity_repo=mock_repo,
            cycle_id="cycle-001",
        )

    blocked.fetch.assert_not_called()
    assert len(result["raw_opportunities"]) == 1
    assert result["sources_queried"] == ["greenhouse"]
