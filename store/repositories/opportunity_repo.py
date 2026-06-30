from __future__ import annotations

import logging
from typing import Any

from pymongo import ReplaceOne
from pymongo.database import Database

from store.db import OPPORTUNITIES
from store.scored_opportunity import ScoredOpportunity

_log = logging.getLogger(__name__)


class OpportunityRepository:
    def __init__(self, db: Database[dict[str, Any]]) -> None:
        self._col = db[OPPORTUNITIES]

    def get_known_external_ids(self, source: str) -> set[str]:
        _log.debug("get_known_external_ids: source=%s", source)
        docs = self._col.find({"raw.source": source}, {"raw.external_id": 1, "_id": 0})
        ids = {d["raw"]["external_id"] for d in docs}
        _log.debug("get_known_external_ids: source=%s found=%d", source, len(ids))
        return ids

    def upsert_one(self, opportunity: ScoredOpportunity) -> None:
        _log.debug("upsert_one: opportunity_id=%s score=%d", opportunity.opportunity_id, opportunity.score)
        self._col.replace_one(
            {"opportunity_id": opportunity.opportunity_id},
            opportunity.model_dump(),
            upsert=True,
        )

    def upsert_many(self, opportunities: list[ScoredOpportunity]) -> None:
        if not opportunities:
            _log.debug("upsert_many: nothing to upsert")
            return
        _log.debug("upsert_many: upserting %d opportunities", len(opportunities))
        ops = [
            ReplaceOne(
                {"opportunity_id": opp.opportunity_id},
                opp.model_dump(),
                upsert=True,
            )
            for opp in opportunities
        ]
        result = self._col.bulk_write(ops)
        _log.debug(
            "upsert_many: upserted=%d modified=%d",
            result.upserted_count,
            result.modified_count,
        )

    def get_by_cycle(self, cycle_id: str) -> list[ScoredOpportunity]:
        _log.debug("get_by_cycle: cycle_id=%s", cycle_id)
        docs = self._col.find({"cycle_id": cycle_id}, {"_id": 0})
        result = [ScoredOpportunity.model_validate(d) for d in docs]
        _log.debug("get_by_cycle: cycle_id=%s found=%d", cycle_id, len(result))
        return result
