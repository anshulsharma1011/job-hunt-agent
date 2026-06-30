from __future__ import annotations

import logging
from typing import Any

from pymongo.database import Database

from store.cycle_record import CycleRecord
from store.db import CYCLES

_log = logging.getLogger(__name__)


class CycleRepository:
    def __init__(self, db: Database[dict[str, Any]]) -> None:
        self._col = db[CYCLES]

    def create(self, cycle: CycleRecord) -> None:
        _log.debug("create: cycle_id=%s", cycle.cycle_id)
        self._col.insert_one(cycle.model_dump())
        _log.debug("create: inserted cycle_id=%s", cycle.cycle_id)

    def update(self, cycle_id: str, updates: dict[str, Any]) -> None:
        _log.debug("update: cycle_id=%s keys=%s", cycle_id, list(updates.keys()))
        self._col.update_one({"cycle_id": cycle_id}, {"$set": updates})

    def get_latest(self) -> CycleRecord | None:
        _log.debug("get_latest: querying most recent cycle")
        doc = self._col.find_one(sort=[("started_at", -1)], projection={"_id": 0})
        if doc is None:
            _log.debug("get_latest: no cycles found")
            return None
        record = CycleRecord.model_validate(doc)
        _log.debug("get_latest: found cycle_id=%s", record.cycle_id)
        return record
