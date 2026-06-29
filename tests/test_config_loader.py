import os
from pathlib import Path

import pytest

from config.loader import load_config, reset_config_cache

CONFIG_DIR = Path("config")


@pytest.fixture(autouse=True)
def clear_cache():
    reset_config_cache()
    yield
    reset_config_cache()


def test_load_config_returns_app_config():
    cfg = load_config(CONFIG_DIR)
    assert cfg.app.name == "job-hunt-agent"
    assert cfg.llm.model == "ollama/llama3.1:8b"
    assert cfg.matching.score_threshold == 70
    assert "greenhouse" in cfg.sources
    assert cfg.mongodb.database == "job_hunt_db"
    assert cfg.scheduler.cron == "0 9,18 * * *"
    assert cfg.output.report_format == "txt"


def test_load_config_is_singleton():
    cfg1 = load_config(CONFIG_DIR)
    cfg2 = load_config(CONFIG_DIR)
    assert cfg1 is cfg2


def test_missing_required_field_raises_validation_error(tmp_path):
    (tmp_path / "app.yaml").write_text("name: test\nenv: development\n")
    (tmp_path / "llm.yaml").write_text("base_url: http://localhost:11434\ntimeout_seconds: 30\ntoken_budget_per_cycle: 1000\n")  # missing model
    (tmp_path / "matching.yaml").write_text("score_threshold: 70\nmax_per_cycle: 10\nmax_concurrent_scoring: 2\n")
    (tmp_path / "sources.yaml").write_text("{}\n")
    (tmp_path / "mongodb.yaml").write_text("uri: mongodb://localhost:27017\ndatabase: db\ntest_database: test_db\n")
    (tmp_path / "scheduler.yaml").write_text("enabled: false\ncron: '0 9 * * *'\n")
    (tmp_path / "output.yaml").write_text("report_dir: ./output\nreport_format: txt\n")

    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        load_config(tmp_path)


def test_env_var_overrides_mongodb_uri(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://override-host:27017")
    cfg = load_config(CONFIG_DIR)
    assert cfg.mongodb.uri == "mongodb://override-host:27017"
