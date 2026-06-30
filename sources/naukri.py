from bs4 import BeautifulSoup

from config.app_config import AppConfig
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria
from store.source_policy import SourcePolicy


class NaukriSource:
    name: str = "naukri"
    policy: SourcePolicy = SourcePolicy.human_assisted

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        raise NotImplementedError(
            "Naukri requires human-assisted fetching. "
            "Use parse_from_html() with HTML copied from the browser."
        )

    def parse_from_html(self, html: str) -> list[RawOpportunity]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[RawOpportunity] = []

        for card in soup.select("article.jobTuple"):
            title_tag = card.select_one("a.title")
            company_tag = card.select_one("a.subTitle")
            location_tag = card.select_one("li.location span")
            link_tag = card.select_one("a.title")

            role_title = title_tag.get_text(strip=True) if title_tag else ""
            company = company_tag.get_text(strip=True) if company_tag else ""
            location = location_tag.get_text(strip=True) if location_tag else ""
            link = link_tag.get("href", "") if link_tag else ""
            if isinstance(link, list):
                link = link[0] if link else ""

            if not role_title or not link:
                continue

            results.append(
                RawOpportunity(
                    source=self.name,
                    source_url=link,
                    external_id=f"naukri:{link}",
                    company=company,
                    role_title=role_title,
                    location=location,
                    description_raw="",
                )
            )

        return results

    def is_enabled(self, config: AppConfig) -> bool:
        return config.sources.naukri.enabled
