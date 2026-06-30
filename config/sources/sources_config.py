from pydantic import BaseModel

from config.sources.adzuna_config import AdzunaConfig
from config.sources.greenhouse_config import GreenhouseConfig
from config.sources.linkedin_config import LinkedInConfig
from config.sources.naukri_config import NaukriConfig
from config.sources.remoteok_config import RemoteOKConfig
from config.sources.weworkremotely_config import WeWorkRemotelyConfig


class SourcesConfig(BaseModel):
    greenhouse: GreenhouseConfig
    adzuna: AdzunaConfig
    remoteok: RemoteOKConfig
    weworkremotely: WeWorkRemotelyConfig
    linkedin: LinkedInConfig
    naukri: NaukriConfig
