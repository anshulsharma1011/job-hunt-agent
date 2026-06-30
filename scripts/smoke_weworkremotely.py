"""
Smoke test for WeWorkRemotelySource — real HTTP, no credentials needed.

Usage:
    python scripts/smoke_weworkremotely.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import load_config
from sources.weworkremotely import WeWorkRemotelySource
from store.search_criteria import SearchCriteria

CRITERIA = SearchCriteria(
    titles=["Software Engineer", "Backend Engineer", "Data Engineer", "Product Manager"],
    locations=["Remote"],
    remote=True,
)


def main() -> None:
    config = load_config()
    source = WeWorkRemotelySource(config)

    feeds = source._feed_urls()
    print(f"Querying We Work Remotely across {len(feeds)} feeds...\n")

    results = source.fetch(CRITERIA)

    print(f"Total: {len(results)} opportunities\n")
    for opp in results[:15]:
        print(f"  [{opp.company or '?'}] {opp.role_title}")
        print(f"    {opp.source_url}")
        print()


if __name__ == "__main__":
    main()
