from unittest.mock import MagicMock, patch

import pytest

from config.app_config import AppConfig
from orchestrator.errors import SourceBlockedError
from sources.adzuna import AdzunaSource
from store.search_criteria import SearchCriteria

_CRITERIA = SearchCriteria(
    titles=["Backend Engineer"],
    locations=["Bangalore"],
    remote=False,
)

_MOCK_JOB = {
    "id": "abc123",
    "title": "Senior Backend Engineer",
    "company": {"display_name": "Acme Corp"},
    "location": {"area": ["Bangalore", "India"]},
    "description": "We need a backend engineer.",
    "redirect_url": "https://www.adzuna.com/jobs/details/abc123",
}

_MOCK_RESPONSE = {"results": [_MOCK_JOB], "count": 1}


def _make_config(app_config: AppConfig, app_id: str = "test_id", api_key: str = "test_key") -> AppConfig:
    app_config.sources.adzuna.app_id = app_id
    app_config.sources.adzuna.api_key = api_key
    return app_config


def test_fetch_returns_raw_opportunities(app_config: AppConfig) -> None:
    _make_config(app_config)
    source = AdzunaSource(app_config)

    with patch("sources.adzuna.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = _MOCK_RESPONSE
        results = source.fetch(_CRITERIA)

    assert len(results) == 1
    opp = results[0]
    assert opp.source == "adzuna"
    assert opp.role_title == "Senior Backend Engineer"
    assert opp.company == "Acme Corp"
    assert opp.external_id == "adzuna:abc123"
    assert "Bangalore" in opp.location


def test_fetch_raises_when_credentials_missing(app_config: AppConfig) -> None:
    app_config.sources.adzuna.app_id = ""
    app_config.sources.adzuna.api_key = ""
    source = AdzunaSource(app_config)

    with pytest.raises(SourceBlockedError):
        source.fetch(_CRITERIA)


def test_fetch_deduplicates_across_titles(app_config: AppConfig) -> None:
    _make_config(app_config)
    criteria = SearchCriteria(titles=["Backend Engineer", "Software Engineer"], locations=["Bangalore"], remote=False)
    source = AdzunaSource(app_config)

    with patch("sources.adzuna.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = _MOCK_RESPONSE
        results = source.fetch(criteria)

    external_ids = [r.external_id for r in results]
    assert len(external_ids) == len(set(external_ids))


def test_fetch_skips_on_request_error(app_config: AppConfig) -> None:
    import requests as req_lib
    _make_config(app_config)
    source = AdzunaSource(app_config)

    with patch("sources.adzuna.requests.get", side_effect=req_lib.RequestException("timeout")):
        results = source.fetch(_CRITERIA)

    assert results == []


def test_is_enabled_reads_config(app_config: AppConfig) -> None:
    _make_config(app_config)
    source = AdzunaSource(app_config)
    assert source.is_enabled(app_config) is True
