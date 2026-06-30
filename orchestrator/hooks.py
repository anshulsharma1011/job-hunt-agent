from __future__ import annotations

import logging

from pydantic import BaseModel, ValidationError

from config.app_config import AppConfig
from orchestrator.errors import (
    BudgetExceededError,
    SchemaValidationError,
    SourceBlockedError,
)
from store.raw_opportunity import RawOpportunity
from store.repositories.opportunity_repo import OpportunityRepository

_log = logging.getLogger(__name__)


def apply_source_policy(source_name: str, config: AppConfig) -> None:
    source_cfg = getattr(config.sources, source_name)
    policy = source_cfg.policy
    _log.debug("apply_source_policy: source=%s policy=%s", source_name, policy)
    if policy == "blocked":
        _log.warning("apply_source_policy: source=%s is blocked by policy", source_name)
        raise SourceBlockedError(f"Source '{source_name}' is blocked by policy.")


def apply_dedup(
    raw: list[RawOpportunity],
    opportunity_repo: OpportunityRepository,
) -> list[RawOpportunity]:
    sources = {opp.source for opp in raw}
    known: set[str] = set()
    for source in sources:
        known |= opportunity_repo.get_known_external_ids(source)
    result = [opp for opp in raw if opp.external_id not in known]
    _log.debug(
        "apply_dedup: input=%d known_ids=%d output=%d duplicates_removed=%d",
        len(raw),
        len(known),
        len(result),
        len(raw) - len(result),
    )
    return result


def validate_output_schema(data: dict[str, object], model: type[BaseModel]) -> BaseModel:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        _log.error("validate_output_schema: schema=%s validation failed", model.__name__)
        raise SchemaValidationError(str(exc)) from exc


def apply_budget_gate(current_spend: float, config: AppConfig) -> None:
    budget: float = config.llm.token_budget_per_cycle
    pct = (current_spend / budget * 100) if budget > 0 else 0.0
    if current_spend >= budget:
        _log.error(
            "apply_budget_gate: spend=%.2f budget=%.2f — EXCEEDED",
            current_spend,
            budget,
        )
        raise BudgetExceededError(
            f"Token spend {current_spend} reached budget limit of {budget}."
        )
    if pct >= 80:
        _log.warning(
            "apply_budget_gate: spend=%.2f budget=%.2f (%.0f%% used)",
            current_spend,
            budget,
            pct,
        )
    else:
        _log.debug(
            "apply_budget_gate: spend=%.2f budget=%.2f (%.0f%% used) — OK",
            current_spend,
            budget,
            pct,
        )
