import pytest

from config.app_config import AppConfig
from config.loader import load_config, reset_config_cache


@pytest.fixture
def app_config() -> AppConfig:
    reset_config_cache()
    return load_config()
