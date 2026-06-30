from pydantic import BaseModel, ValidationError

from config.app_config import AppConfig
from orchestrator.errors import (
    BudgetExceededError,
    SchemaValidationError,
    SourceBlockedError,
)
from store.raw_opportunity import RawOpportunity
from store.repositories.opportunity_repo import OpportunityRepository


def apply_source_policy(source_name: str, config: AppConfig) -> None:
    """Raises SourceBlockedError if the source policy is 'blocked'."""
    source_cfg = getattr(config.sources, source_name)
    if source_cfg.policy == "blocked":
        raise SourceBlockedError(f"Source '{source_name}' is blocked by policy.")



def apply_dedup(
    raw: list[RawOpportunity],
    opportunity_repo: OpportunityRepository,
) -> list[RawOpportunity]:
    """Returns only opportunities whose external_id is not already in MongoDB."""
    sources = {opp.source for opp in raw}
    known: set[str] = set()
    for source in sources:
        known |= opportunity_repo.get_known_external_ids(source)
    return [opp for opp in raw if opp.external_id not in known]


def validate_output_schema(data: dict[str, object], model: type[BaseModel]) -> BaseModel:
    """Parses data into model. Raises SchemaValidationError on failure."""
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise SchemaValidationError(str(exc)) from exc


def apply_budget_gate(current_spend: float, config: AppConfig) -> None:
    """Raises BudgetExceededError if current_spend has reached the per-cycle token budget."""
    budget: float = config.llm.token_budget_per_cycle
    if current_spend >= budget:
        raise BudgetExceededError(
            f"Token spend {current_spend} reached budget limit of {budget}."
        )
