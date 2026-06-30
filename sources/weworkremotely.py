import feedparser

from config.app_config import AppConfig
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria
from store.source_policy import SourcePolicy

_BASE_URL = "https://weworkremotely.com/categories/{category}.rss"

_DEFAULT_CATEGORIES: list[str] = [
    "remote-programming-jobs",
    "remote-devops-sysadmin-jobs",
    "remote-data-science-jobs",
    "remote-product-jobs",
]


class WeWorkRemotelySource:
    name: str = "weworkremotely"
    policy: SourcePolicy = SourcePolicy.allowed

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def _feed_urls(self) -> list[str]:
        source_cfg = self._config.sources.get("weworkremotely")
        categories = (source_cfg.categories if source_cfg and source_cfg.categories else _DEFAULT_CATEGORIES)
        return [_BASE_URL.format(category=cat) for cat in categories]

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        source_cfg = self._config.sources.get("weworkremotely")
        max_per_run = (source_cfg.max_per_run or 50) if source_cfg else 50
        title_keywords = [t.lower() for t in criteria.titles]

        seen_ids: set[str] = set()
        results: list[RawOpportunity] = []

        for feed_url in self._feed_urls():
            if len(results) >= max_per_run:
                break

            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                if len(results) >= max_per_run:
                    break

                raw_title: str = entry.get("title", "")
                link: str = entry.get("link", "")

                if not link or link in seen_ids:
                    continue

                # Title format: "Company: Role Title"
                if ": " in raw_title:
                    company, role_title = raw_title.split(": ", 1)
                else:
                    company, role_title = "", raw_title

                if not any(kw in role_title.lower() for kw in title_keywords):
                    continue

                seen_ids.add(link)
                results.append(
                    RawOpportunity(
                        source=self.name,
                        source_url=link,
                        external_id=f"weworkremotely:{link}",
                        company=company.strip(),
                        role_title=role_title.strip(),
                        location="Remote",
                        description_raw=entry.get("summary", ""),
                    )
                )

        return results

    def is_enabled(self, config: AppConfig) -> bool:
        cfg = config.sources.get("weworkremotely")
        return cfg is not None and cfg.enabled
