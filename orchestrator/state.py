from typing import TypedDict


class CycleState(TypedDict):
    cycle_id: str
    profile: dict[str, object] | None
    search_criteria: dict[str, object] | None
    raw_opportunities: list[dict[str, object]]
    scored_opportunities: list[dict[str, object]]
    shortlisted: list[dict[str, object]]
    rejected: list[dict[str, object]]
    report_path: str | None
    errors: list[str]
    token_spend: float
    sources_queried: list[str]
