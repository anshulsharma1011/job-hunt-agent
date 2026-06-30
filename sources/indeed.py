from urllib.parse import urlencode

import feedparser

from config.app_config import AppConfig
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria
from store.source_policy import SourcePolicy

_RSS_BASE = "https://in.indeed.com/rss"


class IndeedSource:
    name: str = "indeed"
    policy: SourcePolicy = SourcePolicy.allowed

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        source_cfg = self._config.sources.get("indeed")
        location = (source_cfg.location or "India") if source_cfg else "India"

        seen_links: set[str] = set()
        results: list[RawOpportunity] = []

        for title in criteria.titles:
            url = f"{_RSS_BASE}?{urlencode({'q': title, 'l': location})}"
            feed = feedparser.parse(url)

            for entry in feed.entries:
                link: str = entry.get("link", "")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                results.append(
                    RawOpportunity(
                        source=self.name,
                        source_url=link,
                        external_id=f"indeed:{link}",
                        company=entry.get("source", {}).get("title", "") if isinstance(entry.get("source"), dict) else "",
                        role_title=entry.get("title", ""),
                        location=location,
                        description_raw=entry.get("summary", ""),
                    )
                )

        return results

    def is_enabled(self, config: AppConfig) -> bool:
        cfg = config.sources.get("indeed")
        return cfg is not None and cfg.enabled
