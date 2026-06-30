from config.app_config import AppConfig
from sources.adzuna import AdzunaSource
from sources.greenhouse import GreenhouseSource
from sources.interfaces import IJobSource
from sources.linkedin import LinkedInSource
from sources.naukri import NaukriSource
from sources.remoteok import RemoteOKSource


def build_source_registry(config: AppConfig) -> list[IJobSource]:
    all_sources: list[IJobSource] = [
        GreenhouseSource(config),
        AdzunaSource(config),
        RemoteOKSource(config),
        LinkedInSource(config),
        NaukriSource(config),
    ]
    return [s for s in all_sources if s.is_enabled(config)]
