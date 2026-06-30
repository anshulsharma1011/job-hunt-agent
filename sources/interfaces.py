from typing import Protocol, runtime_checkable

from config.app_config import AppConfig
from store.raw_opportunity import RawOpportunity
from store.search_criteria import SearchCriteria
from store.source_policy import SourcePolicy


@runtime_checkable
class IJobSource(Protocol):
    name: str
    policy: SourcePolicy

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]: ...
    def is_enabled(self, config: AppConfig) -> bool: ...
