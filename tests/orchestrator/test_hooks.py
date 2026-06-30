from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from config.app_config import AppConfig
from orchestrator.errors import (
    BudgetExceededError,
    SchemaValidationError,
    SourceBlockedError,
)
from orchestrator.hooks import (
    apply_budget_gate,
    apply_dedup,
    apply_source_policy,
    validate_output_schema,
)
from store.raw_opportunity import RawOpportunity


def _raw(source: str = "greenhouse", external_id: str = "gh-001") -> RawOpportunity:
    return RawOpportunity(
        source=source,
        source_url="https://example.com/jobs/1",
        external_id=external_id,
        company="Acme",
        role_title="Backend Engineer",
        location="Bangalore",
        description_raw="We are hiring.",
    )


# ── apply_source_policy ───────────────────────────────────────────────────────

def test_allowed_source_does_not_raise(app_config: AppConfig) -> None:
    apply_source_policy("greenhouse", app_config)  # must not raise


def test_blocked_source_raises_source_blocked_error(app_config: AppConfig) -> None:
    app_config.sources.greenhouse.policy = "blocked"
    with pytest.raises(SourceBlockedError):
        apply_source_policy("greenhouse", app_config)


def test_human_assisted_source_is_skipped(app_config: AppConfig) -> None:
    with pytest.raises(SourceBlockedError):
        apply_source_policy("naukri", app_config)  # human-assisted must be skipped like blocked



# ── apply_dedup ───────────────────────────────────────────────────────────────

def test_all_new_opportunities_returned() -> None:
    repo = MagicMock()
    repo.get_known_external_ids.return_value = set()
    raw = [_raw(external_id="gh-001"), _raw(external_id="gh-002")]
    result = apply_dedup(raw, repo)
    assert len(result) == 2


def test_all_known_opportunities_dropped() -> None:
    repo = MagicMock()
    repo.get_known_external_ids.return_value = {"gh-001", "gh-002"}
    raw = [_raw(external_id="gh-001"), _raw(external_id="gh-002")]
    result = apply_dedup(raw, repo)
    assert result == []


def test_partial_dedup_returns_only_new() -> None:
    repo = MagicMock()
    repo.get_known_external_ids.return_value = {"gh-001"}
    raw = [_raw(external_id="gh-001"), _raw(external_id="gh-002")]
    result = apply_dedup(raw, repo)
    assert len(result) == 1
    assert result[0].external_id == "gh-002"


# ── validate_output_schema ────────────────────────────────────────────────────

class _SampleModel(BaseModel):
    name: str
    score: int


def test_valid_data_returns_model_instance() -> None:
    result = validate_output_schema({"name": "Backend Engineer", "score": 85}, _SampleModel)
    assert isinstance(result, _SampleModel)
    assert result.score == 85


def test_missing_required_field_raises_schema_validation_error() -> None:
    with pytest.raises(SchemaValidationError):
        validate_output_schema({"name": "Backend Engineer"}, _SampleModel)


def test_wrong_type_raises_schema_validation_error() -> None:
    with pytest.raises(SchemaValidationError):
        validate_output_schema({"name": "Backend Engineer", "score": "not-a-number"}, _SampleModel)


# ── apply_budget_gate ─────────────────────────────────────────────────────────

def test_under_budget_does_not_raise(app_config: AppConfig) -> None:
    app_config.llm.token_budget_per_cycle = 1000
    apply_budget_gate(999.0, app_config)  # must not raise


def test_exactly_at_budget_raises_budget_exceeded_error(app_config: AppConfig) -> None:
    app_config.llm.token_budget_per_cycle = 1000
    with pytest.raises(BudgetExceededError):
        apply_budget_gate(1000.0, app_config)


def test_over_budget_raises_budget_exceeded_error(app_config: AppConfig) -> None:
    app_config.llm.token_budget_per_cycle = 1000
    with pytest.raises(BudgetExceededError):
        apply_budget_gate(1001.0, app_config)
