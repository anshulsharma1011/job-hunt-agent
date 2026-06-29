from pydantic import BaseModel


class SchedulerConfig(BaseModel):
    enabled: bool
    cron: str
