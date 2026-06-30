"""
Smoke test for AdzunaSource — real HTTP, requires ADZUNA_APP_ID and ADZUNA_API_KEY in .env

Usage:
    python scripts/smoke_adzuna.py
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.loader import load_config, reset_config_cache
from orchestrator.errors import SourceBlockedError
from sources.adzuna import AdzunaSource
from store.search_criteria import SearchCriteria

CRITERIA = SearchCriteria(
    titles=["Software Engineer", "Backend Engineer", "Data Engineer", "Product Manager"],
    locations=["Bangalore", "India", "Hyderabad", "Pune", "Chennai", "Mumbai"],
    remote=True,
)


def main() -> None:
    reset_config_cache()
    config = load_config()
    source = AdzunaSource(config)

    cfg = config.sources.get("adzuna")
    if not cfg or not cfg.app_id or not cfg.api_key:
        print("✗ Adzuna credentials not set.")
        print("  Add ADZUNA_APP_ID and ADZUNA_API_KEY to your .env file.")
        print("  Register at: https://developer.adzuna.com")
        sys.exit(1)

    print(f"Querying Adzuna for {len(CRITERIA.titles)} job titles in India...\n")

    try:
        results = source.fetch(CRITERIA)
    except SourceBlockedError as e:
        print(f"✗ {e}")
        sys.exit(1)

    print(f"Total: {len(results)} opportunities\n")

    per_title: dict[str, list] = {}
    for opp in results:
        per_title.setdefault(opp.role_title.split()[0], []).append(opp)

    for opp in results[:15]:
        print(f"  [{opp.company or '?'}] {opp.role_title}")
        print(f"    {opp.location}")
        print(f"    {opp.source_url}")
        print()


if __name__ == "__main__":
    main()
