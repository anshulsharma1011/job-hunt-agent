from __future__ import annotations

from pymongo import ReplaceOne
from pymongo.database import Database

from store.db import OPPORTUNITIES
from store.scored_opportunity import ScoredOpportunity


class OpportunityRepository:
    def __init__(self, db: Database) -> None:
        self._col = db[OPPORTUNITIES]

    def get_known_external_ids(self, source: str) -> set[str]:
        docs = self._col.find({"raw.source": source}, {"raw.external_id": 1, "_id": 0})
        return {d["raw"]["external_id"] for d in docs}

    def upsert_many(self, opportunities: list[ScoredOpportunity]) -> None:
        if not opportunities:
            return
        ops = [
            ReplaceOne(
                {"opportunity_id": opp.opportunity_id},
                opp.model_dump(),
                upsert=True,
            )
            for opp in opportunities
        ]
        self._col.bulk_write(ops)

    def get_by_cycle(self, cycle_id: str) -> list[ScoredOpportunity]:
        docs = self._col.find({"cycle_id": cycle_id}, {"_id": 0})
        return [ScoredOpportunity.model_validate(d) for d in docs]
