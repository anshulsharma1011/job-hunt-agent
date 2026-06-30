from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from config.app_config import AppConfig

_config_cache: Optional[AppConfig] = None


def _read_yaml(path: Path) -> dict[str, object]:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _load_sources(yaml_dir: Path) -> dict[str, dict[str, object]]:
    sources_dir = yaml_dir / "sources"
    sources: dict[str, dict[str, object]] = {}
    for yaml_file in sorted(sources_dir.glob("*.yaml")):
        source_name = yaml_file.stem
        sources[source_name] = dict(_read_yaml(yaml_file))
    return sources


def load_config(config_dir: Path = Path("config")) -> AppConfig:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    yaml_dir = config_dir / "yaml"
    merged: dict[str, object] = {
        "app": _read_yaml(yaml_dir / "app.yaml"),
        "llm": _read_yaml(yaml_dir / "llm.yaml"),
        "matching": _read_yaml(yaml_dir / "matching.yaml"),
        "sources": _load_sources(yaml_dir),
        "mongodb": _read_yaml(yaml_dir / "mongodb.yaml"),
        "scheduler": _read_yaml(yaml_dir / "scheduler.yaml"),
        "output": _read_yaml(yaml_dir / "output.yaml"),
    }

    uri_override = os.environ.get("MONGODB_URI")
    if uri_override:
        mongodb: dict[str, object] = merged["mongodb"]  # type: ignore[assignment]
        mongodb["uri"] = uri_override

    sources: dict[str, dict[str, object]] = merged["sources"]  # type: ignore[assignment]
    adzuna_app_id = os.environ.get("ADZUNA_APP_ID")
    adzuna_api_key = os.environ.get("ADZUNA_API_KEY")
    if adzuna_app_id:
        sources.setdefault("adzuna", {})["app_id"] = adzuna_app_id
    if adzuna_api_key:
        sources.setdefault("adzuna", {})["api_key"] = adzuna_api_key

    _config_cache = AppConfig.model_validate(merged)
    return _config_cache


def reset_config_cache() -> None:
    global _config_cache
    _config_cache = None
