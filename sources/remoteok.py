import requests

from config.app_config import AppConfig
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria
from store.source_policy import SourcePolicy

_API_URL = "https://remoteok.com/api"


class RemoteOKSource:
    name: str = "remoteok"
    policy: SourcePolicy = SourcePolicy.allowed

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        source_cfg = self._config.sources.get("remoteok")
        max_per_run = (source_cfg.max_per_run or 50) if source_cfg else 50

        # RemoteOK returns all jobs; filter client-side by title keywords
        title_keywords = [t.lower() for t in criteria.titles]

        try:
            response = requests.get(
                _API_URL,
                timeout=15,
                headers={"User-Agent": "job-hunt-agent/1.0"},
            )
            response.raise_for_status()
        except requests.RequestException:
            return []

        jobs = response.json()
        # First element is metadata, not a job
        if jobs and isinstance(jobs[0], dict) and "legal" in jobs[0]:
            jobs = jobs[1:]

        results: list[RawOpportunity] = []
        for job in jobs:
            if len(results) >= max_per_run:
                break

            role_title: str = job.get("position", "")
            if not any(kw in role_title.lower() for kw in title_keywords):
                continue

            job_id = str(job.get("id", ""))
            results.append(
                RawOpportunity(
                    source=self.name,
                    source_url=job.get("url", ""),
                    external_id=f"remoteok:{job_id}",
                    company=job.get("company", ""),
                    role_title=role_title,
                    location="Remote",
                    description_raw=job.get("description", ""),
                )
            )

        return results

    def is_enabled(self, config: AppConfig) -> bool:
        cfg = config.sources.get("remoteok")
        return cfg is not None and cfg.enabled
