from pydantic import Field

from config.sources.base import SourcePolicyBase


class GreenhouseConfig(SourcePolicyBase):
    companies: list[str] = Field(default_factory=list)
    max_per_run: int = 200
