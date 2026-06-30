from config.app_config import AppConfig
from sources.greenhouse import GreenhouseSource
from sources.indeed import IndeedSource
from sources.interfaces import IJobSource
from sources.linkedin import LinkedInSource
from sources.naukri import NaukriSource


def build_source_registry(config: AppConfig) -> list[IJobSource]:
    all_sources: list[IJobSource] = [
        GreenhouseSource(config),
        IndeedSource(config),
        LinkedInSource(config),
        NaukriSource(config),
    ]
    return [s for s in all_sources if s.is_enabled(config)]
