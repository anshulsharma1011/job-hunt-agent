from __future__ import annotations

from pymongo.database import Database

from store.cycle_record import CycleRecord
from store.db import CYCLES


class CycleRepository:
    def __init__(self, db: Database) -> None:
        self._col = db[CYCLES]

    def create(self, cycle: CycleRecord) -> None:
        self._col.insert_one(cycle.model_dump())

    def update(self, cycle_id: str, updates: dict) -> None:
        self._col.update_one({"cycle_id": cycle_id}, {"$set": updates})

    def get_latest(self) -> CycleRecord | None:
        doc = self._col.find_one(sort=[("started_at", -1)], projection={"_id": 0})
        if doc is None:
            return None
        return CycleRecord.model_validate(doc)
