from unittest.mock import MagicMock, patch

import pytest

from config.app_config import AppConfig
from sources.greenhouse import GreenhouseSource
from store.search_criteria import SearchCriteria

_CRITERIA = SearchCriteria(
    titles=["Backend Engineer"],
    locations=["Bangalore"],
    remote=False,
)

_MOCK_JOB = {
    "id": 123,
    "title": "Senior Backend Engineer",
    "absolute_url": "https://boards.greenhouse.io/razorpay/jobs/123",
    "location": {"name": "Bangalore, India"},
    "content": "We are looking for a backend engineer...",
}

_MOCK_RESPONSE = {"jobs": [_MOCK_JOB]}


def _mock_get(url: str, timeout: int) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = _MOCK_RESPONSE
    return resp


def test_fetch_returns_raw_opportunities(app_config: AppConfig) -> None:
    source = GreenhouseSource(app_config)
    with patch("sources.greenhouse.requests.get", side_effect=_mock_get):
        results = source.fetch(_CRITERIA)

    assert len(results) > 0
    opp = results[0]
    assert opp.source == "greenhouse"
    assert opp.role_title == "Senior Backend Engineer"
    assert opp.location == "Bangalore, India"
    assert opp.external_id.startswith("greenhouse:postman:")


def test_fetch_filters_by_title_keywords(app_config: AppConfig) -> None:
    source = GreenhouseSource(app_config)
    non_matching_response = {"jobs": [{"id": 1, "title": "Marketing Manager", "absolute_url": "", "location": {}, "content": ""}]}

    with patch("sources.greenhouse.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = non_matching_response
        results = source.fetch(_CRITERIA)

    assert results == []


def test_is_enabled_reads_config(app_config: AppConfig) -> None:
    source = GreenhouseSource(app_config)
    assert source.is_enabled(app_config) is True


def test_is_enabled_false_when_disabled(app_config: AppConfig) -> None:
    app_config.sources["greenhouse"].enabled = False
    source = GreenhouseSource(app_config)
    assert source.is_enabled(app_config) is False


def test_fetch_skips_failed_requests(app_config: AppConfig) -> None:
    import requests as req_lib

    source = GreenhouseSource(app_config)

    with patch("sources.greenhouse.requests.get", side_effect=req_lib.RequestException("timeout")):
        results = source.fetch(_CRITERIA)

    assert results == []
