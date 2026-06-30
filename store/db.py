from __future__ import annotations

from typing import Any, Optional

from pymongo import MongoClient
from pymongo.database import Database

from config.mongo_config import MongoConfig

PROFILES = "profiles"
OPPORTUNITIES = "opportunities"
CYCLES = "cycles"
CHECKPOINTS = "checkpoints"

_client: Optional[MongoClient[dict[str, Any]]] = None


def get_client(config: MongoConfig) -> MongoClient[dict[str, Any]]:
    global _client
    if _client is None:
        _client = MongoClient(config.uri)
    return _client


def get_db(config: MongoConfig) -> Database[dict[str, Any]]:
    return get_client(config)[config.database]


def reset_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
