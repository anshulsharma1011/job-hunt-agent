# T16 — Unit Tests: Agents + Hooks

**Status:** `pending`
**Depends on:** T9, T11, T12, T13

## Goal
Final review pass to ensure full unit test coverage across all agents and all hook functions. Individual test files are written per task — this task ensures nothing is missing.

## Checklist

### Hook Tests (`tests/orchestrator/test_hooks.py`) — written in T9
- [ ] `apply_source_policy` — allowed, blocked, human-assisted
- [ ] `apply_rate_limit` — within, at, above limit
- [ ] `apply_dedup` — all new, all known, partial
- [ ] `validate_output_schema` — valid, missing field, wrong type
- [ ] `apply_budget_gate` — under, at, over

### Profile Agent (`tests/agents/test_profile_agent.py`) — written in T11
- [ ] Happy path returns `ProfileDoc` + `SearchCriteria`
- [ ] LLM called with rendered prompt
- [ ] Missing PDF raises `FileNotFoundError`
- [ ] `LLMTimeoutError` propagates
- [ ] `SchemaValidationError` propagates

### Discovery + Match Agent (`tests/agents/test_discovery_match_agent.py`) — written in T12
- [ ] Returns correct shortlisted and rejected lists
- [ ] `max_per_cycle` cap enforced
- [ ] Dedup called before scoring
- [ ] Concurrent scoring via `ThreadPoolExecutor`
- [ ] Score below threshold goes to rejected
- [ ] Source policy applied per source

### Reporter Agent (`tests/agents/test_reporter_agent.py`) — written in T13
- [ ] Report file created
- [ ] Shortlisted roles in output
- [ ] Summary counts correct
- [ ] File named with cycle ID
- [ ] No LLM or DB calls made

## Final Steps

1. Run `pytest tests/agents/ tests/orchestrator/test_hooks.py -v` — all must pass
2. Run `mypy agents/ orchestrator/hooks.py` — no errors
3. Review coverage: `pytest --tb=short -q` — no skipped or xfail tests
4. Commit if any gaps were closed
