from urllib.parse import urlencode

import feedparser

from config.app_config import AppConfig
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria
from store.source_policy import SourcePolicy

_RSS_BASE = "https://www.linkedin.com/jobs/search"


class LinkedInSource:
    name: str = "linkedin"
    policy: SourcePolicy = SourcePolicy.allowed

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        source_cfg = self._config.sources.linkedin
        max_requests = source_cfg.max_requests_per_cycle

        results: list[RawOpportunity] = []
        requests_made = 0

        for title in criteria.titles:
            if requests_made >= max_requests:
                break

            for location in criteria.locations:
                if requests_made >= max_requests:
                    break

                params = {"keywords": title, "location": location, "f_TPR": "r86400", "trk": "public_jobs_jobs-search-bar_search-submit"}
                url = f"{_RSS_BASE}?{urlencode(params)}"
                feed = feedparser.parse(url)
                requests_made += 1

                for entry in feed.entries:
                    link: str = entry.get("link", "")
                    results.append(
                        RawOpportunity(
                            source=self.name,
                            source_url=link,
                            external_id=f"linkedin:{link}",
                            company=entry.get("author", ""),
                            role_title=entry.get("title", ""),
                            location=location,
                            description_raw=entry.get("summary", ""),
                        )
                    )

        return results

    def is_enabled(self, config: AppConfig) -> bool:
        return config.sources.linkedin.enabled
