from urllib.parse import urlencode

import requests

from config.app_config import AppConfig
from orchestrator.errors import SourceBlockedError
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria
from store.source_policy import SourcePolicy

_API_BASE = "https://api.adzuna.com/v1/api/jobs/in/search/{page}"


class AdzunaSource:
    name: str = "adzuna"
    policy: SourcePolicy = SourcePolicy.allowed

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        source_cfg = self._config.sources.adzuna
        if not source_cfg.app_id or not source_cfg.api_key:
            raise SourceBlockedError(
                "Adzuna credentials missing — set ADZUNA_APP_ID and ADZUNA_API_KEY in .env"
            )

        max_per_run = source_cfg.max_per_run
        location = source_cfg.location
        results: list[RawOpportunity] = []
        seen_ids: set[str] = set()

        for title in criteria.titles:
            if len(results) >= max_per_run:
                break

            params = {
                "app_id": source_cfg.app_id,
                "app_key": source_cfg.api_key,  # Adzuna uses app_key not api_key
                "what": title,
                "where": location,
                "results_per_page": min(50, max_per_run - len(results)),
                "content-type": "application/json",
            }
            url = f"{_API_BASE.format(page=1)}?{urlencode(params)}"

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
            except requests.RequestException:
                continue

            for job in response.json().get("results", []):
                job_id: str = str(job.get("id", ""))
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                category = job.get("category", {})
                location_data = job.get("location", {})
                location_str = ", ".join(location_data.get("area", [])) if location_data else ""
                company = job.get("company", {}).get("display_name", "")

                results.append(
                    RawOpportunity(
                        source=self.name,
                        source_url=job.get("redirect_url", ""),
                        external_id=f"adzuna:{job_id}",
                        company=company,
                        role_title=job.get("title", ""),
                        location=location_str,
                        description_raw=job.get("description", ""),
                    )
                )

        return results

    def is_enabled(self, config: AppConfig) -> bool:
        return config.sources.adzuna.enabled
