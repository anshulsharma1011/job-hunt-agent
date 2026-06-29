from datetime import datetime

from pydantic import BaseModel, Field


class CycleRecord(BaseModel):
    cycle_id: str
    started_at: datetime
    completed_at: datetime | None = None
    sources_queried: list[str] = Field(default_factory=list)
    discovered_count: int = 0
    shortlisted_count: int = 0
    rejected_count: int = 0
    token_spend: float = 0.0
    model_used: str = ""
    report_path: str | None = None
    errors: list[str] = Field(default_factory=list)
