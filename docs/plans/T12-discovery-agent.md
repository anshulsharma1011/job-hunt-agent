# T12 — Discovery + Match Agent

**Status:** `pending`
**Depends on:** T5, T6, T7

## Goal
Fetch from all enabled sources → dedup → score each against profile → return shortlisted and rejected lists.

## Files to Create

```
agents/discovery_match_agent.py
tests/agents/test_discovery_match_agent.py
```

## `agents/discovery_match_agent.py`

```python
class DiscoveryMatchAgent:
    def __init__(
        self,
        llm: LLMClient,
        sources: list[IJobSource],
        config: AppConfig,
    ):
        self._llm = llm
        self._sources = sources
        self._config = config
        self._prompt = load_prompt("job_scoring")

    def run(
        self,
        criteria: SearchCriteria,
        profile: ProfileDoc,
        opportunity_repo: OpportunityRepository,
    ) -> tuple[list[ScoredOpportunity], list[ScoredOpportunity]]:
        """Returns (shortlisted, rejected)."""
        raw = self._fetch_all(criteria)
        deduped = apply_dedup(raw, opportunity_repo)
        scored = self._score_batch(deduped, profile)
        threshold = self._config.matching.score_threshold
        shortlisted = [o for o in scored if o.score >= threshold]
        rejected = [o for o in scored if o.score < threshold]
        return shortlisted, rejected

    def _fetch_all(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        results = []
        for source in self._sources:
            apply_source_policy(source.name, self._config)
            results.extend(source.fetch(criteria))
            if len(results) >= self._config.matching.max_per_cycle:
                break
        return results[:self._config.matching.max_per_cycle]

    def _score(self, opp: RawOpportunity, profile: ProfileDoc) -> ScoredOpportunity:
        user_msg = self._prompt.render_user(
            seniority=profile.seniority,
            experience_years=profile.experience_years,
            skills=profile.skills,
            titles=profile.preferences.titles,
            locations=profile.preferences.locations,
            remote=profile.preferences.remote,
            company=opp.company,
            role_title=opp.role_title,
            location=opp.location,
            description_raw=opp.description_raw,
        )
        result = self._llm.complete_json(
            system=self._prompt.system,
            user=user_msg,
            schema=_ScoreResult,           # internal Pydantic model for LLM response
        )
        return ScoredOpportunity(
            opportunity_id=f"opp_{uuid4().hex[:8]}",
            cycle_id="",                   # set by caller
            raw=opp,
            score=result.score,
            fit_rationale=result.fit_rationale,
            red_flags=result.red_flags,
            recommended_track=result.recommended_track,
            lifecycle_state=LifecycleState.scored,
            history=[LifecycleEvent(state=LifecycleState.scored)],
        )

    def _score_batch(
        self, opps: list[RawOpportunity], profile: ProfileDoc
    ) -> list[ScoredOpportunity]:
        max_workers = self._config.matching.max_concurrent_scoring
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._score, opp, profile) for opp in opps]
            return [f.result() for f in futures]
```

**`_ScoreResult` (internal model — not exported):**
```python
class _ScoreResult(BaseModel):
    score: int
    fit_rationale: list[str]
    red_flags: list[str]
    recommended_track: RecommendedTrack
```

## Tests

Mock `LLMClient` and `IJobSource` — no real network or LLM calls.

```
tests/agents/test_discovery_match_agent.py
  - test_run_returns_shortlisted_and_rejected
  - test_fetch_all_respects_max_per_cycle
  - test_dedup_called_before_scoring
  - test_score_batch_concurrent_scoring
  - test_score_below_threshold_goes_to_rejected
  - test_source_policy_applied_per_source
```

## Steps

1. Define `_ScoreResult` internal model at top of file
2. Write `__init__` — load scoring prompt
3. Write `_score()` — render prompt, call LLM, build `ScoredOpportunity`
4. Write `_score_batch()` — `ThreadPoolExecutor`
5. Write `_fetch_all()` — iterate sources with policy check and cap
6. Write `run()` — orchestrate all above, split by threshold
7. Write tests
8. Run `pytest tests/agents/test_discovery_match_agent.py` — must pass
9. Run `mypy agents/discovery_match_agent.py` — must pass
10. Commit
