from pydantic import BaseModel

from config.llm_config import LLMConfig
from config.matching_config import MatchingConfig
from config.mongo_config import MongoConfig
from config.output_config import OutputConfig
from config.scheduler_config import SchedulerConfig
from config.source_config import SourcePolicyConfig


class _AppSection(BaseModel):
    name: str
    env: str


class AppConfig(BaseModel):
    app: _AppSection
    llm: LLMConfig
    matching: MatchingConfig
    sources: dict[str, SourcePolicyConfig]
    mongodb: MongoConfig
    scheduler: SchedulerConfig
    output: OutputConfig
