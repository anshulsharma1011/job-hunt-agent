"""
Debug script — decodes the checkpoints collection from checkpointing_db and
prints every document in full, human-readable form.

Usage:
    python scripts/debug_checkpoints_full.py
    python scripts/debug_checkpoints_full.py --thread <cycle_id>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import msgpack
from pymongo import MongoClient

from config.loader import load_config


def decode_msgpack(raw: object) -> object:
    if isinstance(raw, bytes):
        try:
            return msgpack.unpackb(raw, raw=False)
        except Exception:
            return "<decode error>"
    return raw


def main(thread_filter: str | None = None) -> None:
    config = load_config()
    client: MongoClient = MongoClient(config.mongodb.uri)  # type: ignore[type-arg]
    db = client["checkpointing_db"]

    query: dict[str, object] = {}
    if thread_filter:
        query["thread_id"] = thread_filter

    docs = list(db["checkpoints"].find(query, {"_id": 0}).sort("checkpoint_id", 1))

    if not docs:
        print("No checkpoints found" + (f" for thread {thread_filter}" if thread_filter else "") + ".")
        return

    for doc in docs:
        doc["checkpoint"] = decode_msgpack(doc.get("checkpoint"))
        doc["metadata"] = decode_msgpack(doc.get("metadata"))
        print(json.dumps(doc, default=str, indent=2))
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decode LangGraph checkpoints collection")
    parser.add_argument("--thread", metavar="CYCLE_ID", help="Filter to a specific cycle ID")
    args = parser.parse_args()
    main(thread_filter=args.thread)
