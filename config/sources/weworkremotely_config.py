from pydantic import Field

from config.sources.base import SourcePolicyBase


class WeWorkRemotelyConfig(SourcePolicyBase):
    categories: list[str] = Field(default_factory=list)
    max_per_run: int = 50
