from unittest.mock import patch

import pytest

from config.app_config import AppConfig
from sources.remoteok import RemoteOKSource
from store.search_criteria import SearchCriteria

_CRITERIA = SearchCriteria(
    titles=["Backend Engineer"],
    locations=["Remote"],
    remote=True,
)

_METADATA = {"legal": "RemoteOK API - remoteok.com"}

_MOCK_JOBS = [
    _METADATA,
    {
        "id": "101",
        "position": "Senior Backend Engineer",
        "company": "Acme Corp",
        "url": "https://remoteok.com/jobs/101",
        "description": "Backend role.",
        "tags": ["python", "backend"],
    },
    {
        "id": "102",
        "position": "Data Engineer",
        "company": "Foo Inc",
        "url": "https://remoteok.com/jobs/102",
        "description": "Data engineering role.",
        "tags": ["spark", "data"],
    },
]


def test_fetch_returns_matching_opportunities(app_config: AppConfig) -> None:
    source = RemoteOKSource(app_config)

    with patch("sources.remoteok.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = _MOCK_JOBS
        results = source.fetch(_CRITERIA)

    assert len(results) == 1
    assert results[0].role_title == "Senior Backend Engineer"
    assert results[0].source == "remoteok"
    assert results[0].location == "Remote"
    assert results[0].external_id == "remoteok:101"


def test_fetch_filters_by_title_keywords(app_config: AppConfig) -> None:
    source = RemoteOKSource(app_config)
    criteria = SearchCriteria(titles=["Data Engineer"], locations=["Remote"], remote=True)

    with patch("sources.remoteok.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = _MOCK_JOBS
        results = source.fetch(criteria)

    assert len(results) == 1
    assert results[0].role_title == "Data Engineer"


def test_fetch_skips_metadata_entry(app_config: AppConfig) -> None:
    source = RemoteOKSource(app_config)

    with patch("sources.remoteok.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = _MOCK_JOBS
        results = source.fetch(_CRITERIA)

    assert all(r.external_id != "remoteok:" for r in results)


def test_fetch_skips_on_request_error(app_config: AppConfig) -> None:
    import requests as req_lib
    source = RemoteOKSource(app_config)

    with patch("sources.remoteok.requests.get", side_effect=req_lib.RequestException("timeout")):
        results = source.fetch(_CRITERIA)

    assert results == []


def test_is_enabled_reads_config(app_config: AppConfig) -> None:
    source = RemoteOKSource(app_config)
    assert source.is_enabled(app_config) is True
