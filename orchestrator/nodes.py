from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logging_setup import get_logger
from orchestrator.deps import Deps
from orchestrator.hooks import apply_budget_gate
from orchestrator.state import CycleState
from store.scored_opportunity import ScoredOpportunity


def load_profile_node(state: CycleState, deps: Deps) -> dict[str, object]:
    log = get_logger(__name__, state["cycle_id"])
    t0 = time.perf_counter()
    log.debug("load_profile: started")
    profile = deps.profile_repo.get_active()
    elapsed = time.perf_counter() - t0
    if profile is None:
        log.info("load_profile: no active profile — routing to run_profile_agent (%.3fs)", elapsed)
        return {"profile": None, "search_criteria": None}
    log.debug("load_profile: found profile_id=%s skills=%d", profile.profile_id, len(profile.skills))
    log.info("load_profile: completed in %.3fs → route=profile_exists", elapsed)
    return {
        "profile": profile.model_dump(),
        "search_criteria": profile.preferences.model_dump(),
    }


def run_profile_agent_node(state: CycleState, deps: Deps) -> dict[str, object]:
    log = get_logger(__name__, state["cycle_id"])
    t0 = time.perf_counter()
    log.info("run_profile_agent: started")
    pdf_path = Path(deps.config.app.resume_path)
    log.debug("run_profile_agent: reading PDF from %s", pdf_path)
    result: dict[str, Any] = deps.profile_agent.run(pdf_path)
    profile_doc = result.get("profile_doc")
    if profile_doc is not None:
        deps.profile_repo.save(profile_doc)
        log.debug("run_profile_agent: saved profile_id=%s", profile_doc.profile_id)
    elapsed = time.perf_counter() - t0
    log.info("run_profile_agent: completed in %.3fs", elapsed)
    return {
        "profile": result.get("profile"),
        "search_criteria": result.get("search_criteria"),
    }


def run_discovery_match_node(state: CycleState, deps: Deps) -> dict[str, object]:
    log = get_logger(__name__, state["cycle_id"])
    t0 = time.perf_counter()
    log.info("run_discovery_match: started")
    result: dict[str, Any] = deps.discovery_match_agent.run(state, deps.config)
    apply_budget_gate(float(result.get("token_spend", 0.0)), deps.config)
    elapsed = time.perf_counter() - t0
    discovered = len(result.get("raw_opportunities", []))
    shortlisted = len(result.get("shortlisted", []))
    rejected = len(result.get("rejected", []))
    token_spend = float(result.get("token_spend", 0.0))
    log.debug(
        "run_discovery_match: sources=%s discovered=%d shortlisted=%d rejected=%d",
        result.get("sources_queried", []),
        discovered,
        shortlisted,
        rejected,
    )
    log.info(
        "run_discovery_match: completed in %.3fs — discovered=%d shortlisted=%d rejected=%d token_spend=%.2f",
        elapsed,
        discovered,
        shortlisted,
        rejected,
        token_spend,
    )
    return {
        "raw_opportunities": result.get("raw_opportunities", []),
        "scored_opportunities": result.get("scored_opportunities", []),
        "shortlisted": result.get("shortlisted", []),
        "rejected": result.get("rejected", []),
        "token_spend": result.get("token_spend", 0.0),
        "sources_queried": result.get("sources_queried", []),
    }


def store_results_node(state: CycleState, deps: Deps) -> dict[str, object]:
    log = get_logger(__name__, state["cycle_id"])
    t0 = time.perf_counter()
    total = len(state["shortlisted"]) + len(state["rejected"])
    log.debug("store_results: upserting %d opportunities", total)
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
    elapsed = time.perf_counter() - t0
    log.info(
        "store_results: completed in %.3fs — saved %d shortlisted + %d rejected",
        elapsed,
        len(shortlisted),
        len(rejected),
    )
    return {}


def run_reporter_node(state: CycleState, deps: Deps) -> dict[str, object]:
    log = get_logger(__name__, state["cycle_id"])
    t0 = time.perf_counter()
    log.info("run_reporter: started")
    result: dict[str, object] = deps.reporter_agent.run(state, deps.config)
    report_path = str(result.get("report_path", ""))
    deps.cycle_repo.update(
        state["cycle_id"],
        {
            "completed_at": datetime.now(timezone.utc),
            "report_path": report_path,
        },
    )
    elapsed = time.perf_counter() - t0
    log.info(
        "run_reporter: cycle complete in %.3fs — discovered=%d shortlisted=%d rejected=%d token_spend=%.2f report=%s",
        elapsed,
        len(state["raw_opportunities"]),
        len(state["shortlisted"]),
        len(state["rejected"]),
        float(state["token_spend"]),
        report_path,
    )
    return {"report_path": report_path}
