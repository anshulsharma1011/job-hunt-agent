from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from config.app_config import AppConfig
from llm.client import LLMClient, _extract_json
from orchestrator.errors import SchemaValidationError, SourceBlockedError
from orchestrator.hooks import apply_dedup, apply_source_policy
from prompts.loader import load_prompt
from sources.interfaces import IJobSource
from store.lifecycle_event import LifecycleEvent
from store.lifecycle_state import LifecycleState
from store.profile_doc import ProfileDoc
from store.raw_opportunity import RawOpportunity
from store.recommended_track import RecommendedTrack
from store.repositories.opportunity_repo import OpportunityRepository
from store.scored_opportunity import ScoredOpportunity
from store.search_criteria import SearchCriteria

_log = logging.getLogger(__name__)


class _ScoreResult(BaseModel):
    score: int
    fit_rationale: list[str]
    red_flags: list[str]
    recommended_track: RecommendedTrack


class DiscoveryMatchAgent:
    def __init__(self, llm: LLMClient, sources: list[IJobSource], config: AppConfig) -> None:
        self._llm = llm
        self._sources = sources
        self._config = config
        self._prompt = load_prompt("job_scoring")

    def run(
        self,
        criteria: SearchCriteria,
        profile: ProfileDoc,
        opportunity_repo: OpportunityRepository,
        cycle_id: str,
    ) -> dict[str, object]:
        raw, sources_queried = self._fetch_all(criteria)
        _log.info(
            "run: fetched=%d from sources=%s cycle_id=%s",
            len(raw),
            sources_queried,
            cycle_id,
        )
        deduped = apply_dedup(raw, opportunity_repo)
        cap = self._config.matching.max_per_cycle
        fresh = deduped[:cap]
        _log.debug(
            "run: after_dedup=%d removed=%d fresh_capped=%d cycle_id=%s",
            len(deduped),
            len(raw) - len(deduped),
            len(fresh),
            cycle_id,
        )
        scored, token_spend = self._score_batch(fresh, profile, cycle_id, opportunity_repo)
        threshold = self._config.matching.score_threshold
        shortlisted = [o for o in scored if o.score >= threshold]
        rejected = [o for o in scored if o.score < threshold]
        _log.info(
            "run: scored=%d shortlisted=%d rejected=%d token_spend=%.2f cycle_id=%s",
            len(scored),
            len(shortlisted),
            len(rejected),
            token_spend,
            cycle_id,
        )
        return {
            "raw_opportunities": [r.model_dump() for r in raw],
            "shortlisted": [o.model_dump() for o in shortlisted],
            "rejected": [o.model_dump() for o in rejected],
            "token_spend": token_spend,
            "sources_queried": sources_queried,
        }

    def _fetch_all(self, criteria: SearchCriteria) -> tuple[list[RawOpportunity], list[str]]:
        raw: list[RawOpportunity] = []
        sources_queried: list[str] = []
        for source in self._sources:
            try:
                apply_source_policy(source.name, self._config)
            except SourceBlockedError:
                _log.debug("_fetch_all: source=%s skipped — blocked by policy", source.name)
                continue
            fetched = source.fetch(criteria)
            raw.extend(fetched)
            sources_queried.append(source.name)
            _log.debug(
                "_fetch_all: source=%s fetched=%d total=%d",
                source.name,
                len(fetched),
                len(raw),
            )
        return raw, sources_queried

    def _score(
        self, opp: RawOpportunity, profile: ProfileDoc, cycle_id: str
    ) -> tuple[ScoredOpportunity, int]:
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
        text, tokens = self._llm.complete(system=self._prompt.system, user=user_msg)
        try:
            result = _ScoreResult.model_validate_json(_extract_json(text))
        except ValidationError:
            _log.warning("_score: parse failed for %s — retrying", opp.external_id)
            text2, tokens2 = self._llm.complete(system=self._prompt.system, user=user_msg)
            tokens += tokens2
            try:
                result = _ScoreResult.model_validate_json(_extract_json(text2))
            except ValidationError as exc:
                raise SchemaValidationError(
                    f"Score result did not match schema for {opp.external_id} after retry"
                ) from exc
        scored = ScoredOpportunity(
            opportunity_id=f"opp_{uuid4().hex[:8]}",
            cycle_id=cycle_id,
            raw=opp,
            score=result.score,
            fit_rationale=result.fit_rationale,
            red_flags=result.red_flags,
            recommended_track=result.recommended_track,
            lifecycle_state=LifecycleState.scored,
            history=[LifecycleEvent(state=LifecycleState.scored)],
        )
        _log.debug(
            "_score: %s score=%d track=%s",
            opp.external_id,
            result.score,
            result.recommended_track,
        )
        return scored, tokens

    def _score_batch(
        self,
        opps: list[RawOpportunity],
        profile: ProfileDoc,
        cycle_id: str,
        opportunity_repo: OpportunityRepository,
    ) -> tuple[list[ScoredOpportunity], float]:
        if not opps:
            _log.debug("_score_batch: nothing to score")
            return [], 0.0

        previously_scored = opportunity_repo.get_by_cycle(cycle_id)
        already_scored_ids = {o.raw.external_id for o in previously_scored}
        remaining = [o for o in opps if o.external_id not in already_scored_ids]
        _log.debug(
            "_score_batch: total=%d already_scored=%d to_score=%d",
            len(opps),
            len(already_scored_ids),
            len(remaining),
        )

        total_tokens = 0
        token_lock = threading.Lock()
        new_results: list[ScoredOpportunity] = []
        results_lock = threading.Lock()

        def _score_tracked(opp: RawOpportunity) -> None:
            nonlocal total_tokens
            scored, tokens = self._score(opp, profile, cycle_id)
            opportunity_repo.upsert_one(scored)
            with token_lock:
                total_tokens += tokens
            with results_lock:
                new_results.append(scored)

        max_workers = self._config.matching.max_concurrent_scoring
        _log.debug("_score_batch: scoring %d opps max_workers=%d", len(remaining), max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_score_tracked, opp) for opp in remaining]
            for f in futures:
                f.result()

        return previously_scored + new_results, float(total_tokens)
