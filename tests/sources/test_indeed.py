from unittest.mock import MagicMock, patch

import pytest

from config.app_config import AppConfig
from sources.indeed import IndeedSource
from store.search_criteria import SearchCriteria

_CRITERIA = SearchCriteria(
    titles=["Backend Engineer", "Software Engineer"],
    locations=["Bangalore"],
    remote=False,
)


def _make_entry(title: str, link: str, summary: str = "") -> MagicMock:
    entry = MagicMock()
    entry.get = lambda key, default=None: {
        "title": title,
        "link": link,
        "summary": summary,
        "source": {"title": "Acme Corp"},
    }.get(key, default)
    return entry


def _make_feed(*entries: MagicMock) -> MagicMock:
    feed = MagicMock()
    feed.entries = list(entries)
    return feed


def test_fetch_parses_rss_feed(app_config: AppConfig) -> None:
    source = IndeedSource(app_config)
    entry = _make_entry("Backend Engineer", "https://in.indeed.com/job/1", "Great role")

    with patch("sources.indeed.feedparser.parse", return_value=_make_feed(entry)):
        results = source.fetch(_CRITERIA)

    assert len(results) == 1  # same link across both title feeds — dedup keeps one
    assert results[0].source == "indeed"
    assert results[0].role_title == "Backend Engineer"
    assert results[0].source_url == "https://in.indeed.com/job/1"


def test_fetch_deduplicates_by_link(app_config: AppConfig) -> None:
    source = IndeedSource(app_config)
    duplicate_link = "https://in.indeed.com/job/99"
    entry = _make_entry("Backend Engineer", duplicate_link)

    with patch("sources.indeed.feedparser.parse", return_value=_make_feed(entry, entry)):
        results = source.fetch(_CRITERIA)

    links = [r.source_url for r in results]
    assert len(links) == len(set(links))


def test_is_enabled_reads_config(app_config: AppConfig) -> None:
    source = IndeedSource(app_config)
    assert source.is_enabled(app_config) is True
