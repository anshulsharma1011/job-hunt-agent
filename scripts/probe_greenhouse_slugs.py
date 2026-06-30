"""
Probe the Greenhouse boards API to discover valid company slugs.

Runs HEAD requests concurrently against all candidates in greenhouse_candidates.py
and prints valid slugs ready to paste into config/sources.yaml.

Usage:
    python scripts/probe_greenhouse_slugs.py
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.greenhouse_candidates import CANDIDATES

_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
_WORKERS = 20


def _probe(slug: str, session: requests.Session) -> bool:
    try:
        r = session.head(_API_BASE.format(slug=slug), timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


def main() -> None:
    session = requests.Session()
    session.headers["User-Agent"] = "job-hunt-agent/1.0"

    seen: set[str] = set()
    unique = [(name, slug) for name, slug in CANDIDATES if slug not in seen and not seen.add(slug)]  # type: ignore[func-returns-value]

    print(f"Probing {len(unique)} candidate slugs with {_WORKERS} workers...\n")

    results: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        futures = {pool.submit(_probe, slug, session): (name, slug) for name, slug in unique}
        for future in as_completed(futures):
            name, slug = futures[future]
            ok = future.result()
            results[slug] = ok
            print(f"  {'✓' if ok else '✗'}  {slug:<35} ({name})")
            time.sleep(0.15)

    valid = [slug for _, slug in unique if results.get(slug)]
    print(f"\n{'=' * 55}")
    print(f"Valid slugs ({len(valid)} found):\n")
    print("companies:")
    for slug in valid:
        print(f"  - {slug}")


if __name__ == "__main__":
    main()
