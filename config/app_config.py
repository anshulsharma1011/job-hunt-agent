from pydantic import BaseModel

from config.app_section import AppSection
from config.llm_config import LLMConfig
from config.matching_config import MatchingConfig
from config.mongo_config import MongoConfig
from config.output_config import OutputConfig
from config.scheduler_config import SchedulerConfig
from config.sources.sources_config import SourcesConfig


class AppConfig(BaseModel):
    app: AppSection
    llm: LLMConfig
    matching: MatchingConfig
    sources: SourcesConfig
    mongodb: MongoConfig
    scheduler: SchedulerConfig
    output: OutputConfig
