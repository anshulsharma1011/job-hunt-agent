"""
Smoke test for GreenhouseSource — real HTTP, no mocks.
Fetches jobs concurrently across all configured company slugs.

Usage:
    python scripts/smoke_greenhouse.py
"""
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import load_config
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria

_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
_WORKERS = 10

CRITERIA = SearchCriteria(
    titles=["Software Engineer", "Backend Engineer", "Data Engineer", "Product Manager"],
    locations=["Bangalore", "India", "Hyderabad", "Pune", "Chennai", "Mumbai"],
    remote=True,
)


def _fetch_slug(slug: str, title_keywords: list[str], session: requests.Session) -> list[RawOpportunity]:  # noqa: C901
    try:
        r = session.get(_API_BASE.format(slug=slug), timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  [skip] {slug}: {e}")
        return []

    location_keywords = [loc.lower() for loc in CRITERIA.locations]
    results = []
    for job in r.json().get("jobs", []):
        title: str = job.get("title", "")
        if not any(kw in title.lower() for kw in title_keywords):
            continue
        loc_data = job.get("location", {})
        location: str = loc_data.get("name", "") if isinstance(loc_data, dict) else ""
        location_lower = location.lower()
        is_remote = "remote" in location_lower
        matches_location = any(loc in location_lower for loc in location_keywords)
        if not matches_location and not (CRITERIA.remote and is_remote):
            continue
        results.append(
            RawOpportunity(
                source="greenhouse",
                source_url=job.get("absolute_url", ""),
                external_id=f"greenhouse:{slug}:{job.get('id', '')}",
                company=slug,
                role_title=title,
                location=location,
                description_raw=job.get("content", ""),
            )
        )
    return results


def main() -> None:
    config = load_config()
    slugs = config.sources["greenhouse"].companies
    keywords = [t.lower() for t in CRITERIA.titles]

    print(f"Querying {len(slugs)} slugs with {_WORKERS} workers...\n")

    session = requests.Session()
    session.headers["User-Agent"] = "job-hunt-agent/1.0"

    per_company: dict[str, list[RawOpportunity]] = {}
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        futures = {pool.submit(_fetch_slug, slug, keywords, session): slug for slug in slugs}
        for future in as_completed(futures):
            slug = futures[future]
            per_company[slug] = future.result()

    total = sum(len(v) for v in per_company.values())
    print(f"Total: {total} opportunities\n")
    for slug in slugs:
        results = per_company.get(slug, [])
        if not results:
            continue
        print(f"  [{slug}] {len(results)} match(es)")
        for opp in results[:3]:
            print(f"    • {opp.role_title}  —  {opp.location}")
        print()


if __name__ == "__main__":
    main()
