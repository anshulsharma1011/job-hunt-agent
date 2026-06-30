import requests

from config.app_config import AppConfig
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria
from store.source_policy import SourcePolicy

_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


class GreenhouseSource:
    name: str = "greenhouse"
    policy: SourcePolicy = SourcePolicy.allowed

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        source_cfg = self._config.sources.get("greenhouse")
        if not source_cfg or not source_cfg.companies:
            return []

        title_keywords = [t.lower() for t in criteria.titles]
        results: list[RawOpportunity] = []

        for slug in source_cfg.companies:
            url = _API_BASE.format(slug=slug)
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
            except requests.RequestException:
                continue

            jobs = response.json().get("jobs", [])

            for job in jobs:
                job_title: str = job.get("title", "")
                if not any(kw in job_title.lower() for kw in title_keywords):
                    continue

                job_id = str(job.get("id", ""))
                location_data = job.get("location", {})
                location = location_data.get("name", "") if isinstance(location_data, dict) else ""

                results.append(
                    RawOpportunity(
                        source=self.name,
                        source_url=job.get("absolute_url", ""),
                        external_id=f"greenhouse:{slug}:{job_id}",
                        company=slug,
                        role_title=job_title,
                        location=location,
                        description_raw=job.get("content", ""),
                    )
                )

        return results

    def is_enabled(self, config: AppConfig) -> bool:
        cfg = config.sources.get("greenhouse")
        return cfg is not None and cfg.enabled
