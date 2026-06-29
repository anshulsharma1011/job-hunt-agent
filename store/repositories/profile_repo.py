from __future__ import annotations

from pymongo.database import Database

from store.db import PROFILES
from store.profile_doc import ProfileDoc


class ProfileRepository:
    def __init__(self, db: Database) -> None:
        self._col = db[PROFILES]

    def get_active(self) -> ProfileDoc | None:
        doc = self._col.find_one({"is_active": True}, {"_id": 0})
        if doc is None:
            return None
        return ProfileDoc.model_validate(doc)

    def save(self, profile: ProfileDoc) -> None:
        self.deactivate_all()
        self._col.insert_one(profile.model_dump())

    def deactivate_all(self) -> None:
        self._col.update_many({}, {"$set": {"is_active": False}})
