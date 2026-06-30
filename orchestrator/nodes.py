from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.deps import Deps
from orchestrator.hooks import apply_budget_gate
from orchestrator.state import CycleState
from store.scored_opportunity import ScoredOpportunity


def load_profile_node(state: CycleState, deps: Deps) -> dict[str, object]:
    profile = deps.profile_repo.get_active()
    if profile is None:
        return {"profile": None, "search_criteria": None}
    return {
        "profile": profile.model_dump(),
        "search_criteria": profile.preferences.model_dump(),
    }


def run_profile_agent_node(state: CycleState, deps: Deps) -> dict[str, object]:
    pdf_path = Path(deps.config.app.resume_path)
    result: dict[str, Any] = deps.profile_agent.run(pdf_path)
    profile_doc = result.get("profile_doc")
    if profile_doc is not None:
        deps.profile_repo.save(profile_doc)
    return {
        "profile": result.get("profile"),
        "search_criteria": result.get("search_criteria"),
    }


def run_discovery_match_node(state: CycleState, deps: Deps) -> dict[str, object]:
    result: dict[str, Any] = deps.discovery_match_agent.run(state, deps.config)
    apply_budget_gate(float(result.get("token_spend", 0.0)), deps.config)
    return {
        "raw_opportunities": result.get("raw_opportunities", []),
        "scored_opportunities": result.get("scored_opportunities", []),
        "shortlisted": result.get("shortlisted", []),
        "rejected": result.get("rejected", []),
        "token_spend": result.get("token_spend", 0.0),
        "sources_queried": result.get("sources_queried", []),
    }


def store_results_node(state: CycleState, deps: Deps) -> dict[str, object]:
    shortlisted = [ScoredOpportunity.model_validate(d) for d in state["shortlisted"]]
    rejected = [ScoredOpportunity.model_validate(d) for d in state["rejected"]]
    deps.opportunity_repo.upsert_many(shortlisted + rejected)
    deps.cycle_repo.update(
        state["cycle_id"],
        {
            "discovered_count": len(state["raw_opportunities"]),
            "shortlisted_count": len(state["shortlisted"]),
            "rejected_count": len(state["rejected"]),
            "token_spend": state["token_spend"],
            "sources_queried": state["sources_queried"],
            "errors": state["errors"],
        },
    )
    return {}


def run_reporter_node(state: CycleState, deps: Deps) -> dict[str, object]:
    result: dict[str, object] = deps.reporter_agent.run(state, deps.config)
    report_path = str(result.get("report_path", ""))
    deps.cycle_repo.update(
        state["cycle_id"],
        {
            "completed_at": datetime.now(timezone.utc),
            "report_path": report_path,
        },
    )
    return {"report_path": report_path}
