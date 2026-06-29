# T7 — Source Layer

**Status:** `pending`
**Depends on:** T2, T3

## Goal
`IJobSource` Protocol, source registry, and four concrete source classes. Agent code only depends on the interface — never on concrete classes.

## Files to Create

```
sources/interfaces.py
sources/registry.py
sources/greenhouse.py
sources/indeed.py
sources/linkedin.py
sources/naukri.py
tests/sources/test_greenhouse.py
tests/sources/test_indeed.py
tests/sources/test_naukri.py
```

## `sources/interfaces.py`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class IJobSource(Protocol):
    name: str
    policy: SourcePolicy

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]: ...
    def is_enabled(self, config: AppConfig) -> bool: ...
```

Why `Protocol` over ABC: structural subtyping — any class with the right shape satisfies the interface without explicit inheritance. Makes third-party sources drop-in compatible.

## `sources/registry.py`

```python
def build_source_registry(config: AppConfig) -> list[IJobSource]:
    all_sources: list[IJobSource] = [
        GreenhouseSource(config),
        IndeedSource(config),
        LinkedInSource(config),
        NaukriSource(config),
    ]
    return [s for s in all_sources if s.is_enabled(config)]
```

## Concrete Sources

**`sources/greenhouse.py`**
- `name = "greenhouse"`, `policy = SourcePolicy.allowed`
- Endpoint: `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- If `config.sources["greenhouse"].companies` is empty, use a curated list of India-active tech companies
- Filter returned jobs by title keywords from `criteria.titles`
- Map API response fields → `RawOpportunity`

**`sources/indeed.py`**
- `name = "indeed"`, `policy = SourcePolicy.allowed`
- RSS: `https://in.indeed.com/rss?q={title}&l={location}`
- Build one RSS URL per title in `criteria.titles`, parse via `feedparser`
- Deduplicate by `link` before returning

**`sources/linkedin.py`**
- `name = "linkedin"`, `policy = SourcePolicy.allowed`
- RSS feed URL built from criteria
- Hard cap: `config.sources["linkedin"].max_requests_per_cycle` — stop after N requests

**`sources/naukri.py`**
- `name = "naukri"`, `policy = SourcePolicy.human_assisted`
- `fetch()` raises `NotImplementedError` — always
- `parse_from_html(html: str) -> list[RawOpportunity]` — BeautifulSoup parse, no network calls

## Tests

All source tests mock HTTP — no real network calls.

```
tests/sources/test_greenhouse.py
  - test_fetch_returns_raw_opportunities
  - test_fetch_filters_by_title_keywords
  - test_is_enabled_reads_config

tests/sources/test_indeed.py
  - test_fetch_parses_rss_feed
  - test_fetch_deduplicates_by_link

tests/sources/test_naukri.py
  - test_fetch_raises_not_implemented
  - test_parse_from_html_returns_opportunities
```

## Steps

1. Write `sources/interfaces.py`
2. Write all four concrete source classes
3. Write `sources/registry.py`
4. Write tests (mock `requests.get` and `feedparser.parse`)
5. Run `pytest tests/sources/` — must pass
6. Run `mypy sources/` — must pass
7. Commit
