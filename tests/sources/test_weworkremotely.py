from unittest.mock import MagicMock, patch

import pytest

from config.app_config import AppConfig
from sources.weworkremotely import WeWorkRemotelySource
from store.search_criteria import SearchCriteria

_CRITERIA = SearchCriteria(
    titles=["Backend Engineer"],
    locations=["Remote"],
    remote=True,
)


def _make_entry(title: str, link: str, summary: str = "") -> MagicMock:
    entry = MagicMock()
    entry.get = lambda key, default=None: {
        "title": title,
        "link": link,
        "summary": summary,
    }.get(key, default)
    return entry


def _make_feed(*entries: MagicMock) -> MagicMock:
    feed = MagicMock()
    feed.entries = list(entries)
    return feed


def test_fetch_parses_company_and_role_from_title(app_config: AppConfig) -> None:
    source = WeWorkRemotelySource(app_config)
    entry = _make_entry("Acme Corp: Senior Backend Engineer", "https://weworkremotely.com/jobs/1")

    with patch("sources.weworkremotely.feedparser.parse", return_value=_make_feed(entry)):
        results = source.fetch(_CRITERIA)

    assert len(results) == 1
    assert results[0].company == "Acme Corp"
    assert results[0].role_title == "Senior Backend Engineer"
    assert results[0].source == "weworkremotely"
    assert results[0].location == "Remote"
    assert results[0].external_id == "weworkremotely:https://weworkremotely.com/jobs/1"


def test_fetch_filters_by_title_keywords(app_config: AppConfig) -> None:
    source = WeWorkRemotelySource(app_config)
    entry = _make_entry("Acme Corp: Marketing Manager", "https://weworkremotely.com/jobs/2")

    with patch("sources.weworkremotely.feedparser.parse", return_value=_make_feed(entry)):
        results = source.fetch(_CRITERIA)

    assert results == []


def test_fetch_deduplicates_across_feeds(app_config: AppConfig) -> None:
    source = WeWorkRemotelySource(app_config)
    entry = _make_entry("Acme Corp: Backend Engineer", "https://weworkremotely.com/jobs/1")

    with patch("sources.weworkremotely.feedparser.parse", return_value=_make_feed(entry)):
        results = source.fetch(_CRITERIA)

    links = [r.source_url for r in results]
    assert len(links) == len(set(links))


def test_fetch_handles_title_without_colon(app_config: AppConfig) -> None:
    source = WeWorkRemotelySource(app_config)
    entry = _make_entry("Backend Engineer", "https://weworkremotely.com/jobs/3")

    with patch("sources.weworkremotely.feedparser.parse", return_value=_make_feed(entry)):
        results = source.fetch(_CRITERIA)

    assert len(results) == 1
    assert results[0].company == ""
    assert results[0].role_title == "Backend Engineer"


def test_is_enabled_reads_config(app_config: AppConfig) -> None:
    source = WeWorkRemotelySource(app_config)
    assert source.is_enabled(app_config) is True
