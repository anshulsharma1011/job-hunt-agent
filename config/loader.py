from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from config.app_config import AppConfig

_config_cache: Optional[AppConfig] = None


def _read_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_config(config_dir: Path = Path("config")) -> AppConfig:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    merged = {
        "app": _read_yaml(config_dir / "app.yaml"),
        "llm": _read_yaml(config_dir / "llm.yaml"),
        "matching": _read_yaml(config_dir / "matching.yaml"),
        "sources": _read_yaml(config_dir / "sources.yaml"),
        "mongodb": _read_yaml(config_dir / "mongodb.yaml"),
        "scheduler": _read_yaml(config_dir / "scheduler.yaml"),
        "output": _read_yaml(config_dir / "output.yaml"),
    }

    uri_override = os.environ.get("MONGODB_URI")
    if uri_override:
        merged["mongodb"]["uri"] = uri_override

    _config_cache = AppConfig.model_validate(merged)
    return _config_cache


def reset_config_cache() -> None:
    global _config_cache
    _config_cache = None
