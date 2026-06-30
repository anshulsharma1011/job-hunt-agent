from __future__ import annotations

import logging
from typing import Any

from pymongo.database import Database

from store.db import PROFILES
from store.profile_doc import ProfileDoc

_log = logging.getLogger(__name__)


class ProfileRepository:
    def __init__(self, db: Database[dict[str, Any]]) -> None:
        self._col = db[PROFILES]

    def get_active(self) -> ProfileDoc | None:
        _log.debug("get_active: query={is_active: true}")
        doc = self._col.find_one({"is_active": True}, {"_id": 0})
        if doc is None:
            _log.debug("get_active: no active profile found")
            return None
        profile = ProfileDoc.model_validate(doc)
        _log.debug("get_active: found profile_id=%s", profile.profile_id)
        return profile

    def save(self, profile: ProfileDoc) -> None:
        _log.debug("save: deactivating existing profiles then inserting profile_id=%s", profile.profile_id)
        self.deactivate_all()
        self._col.insert_one(profile.model_dump())
        _log.debug("save: inserted profile_id=%s", profile.profile_id)

    def deactivate_all(self) -> None:
        result = self._col.update_many({}, {"$set": {"is_active": False}})
        _log.debug("deactivate_all: modified=%d", result.modified_count)
