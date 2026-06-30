from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Any, MutableMapping

from config.log_config import LogConfig


class CycleAdapter(logging.LoggerAdapter):  # type: ignore[type-arg]
    def process(self, msg: Any, kwargs: MutableMapping[str, Any]) -> tuple[Any, MutableMapping[str, Any]]:
        cycle_id = self.extra.get("cycle_id", "") if self.extra else ""
        prefix = f"[cycle={cycle_id}] " if cycle_id else ""
        return f"{prefix}{msg}", kwargs


def get_logger(name: str, cycle_id: str = "") -> CycleAdapter:
    return CycleAdapter(logging.getLogger(name), {"cycle_id": cycle_id})


def setup_logging(config: LogConfig) -> None:
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        root.handlers.clear()

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    root.addHandler(stream)

    if config.log_to_file:
        log_dir = Path(config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
