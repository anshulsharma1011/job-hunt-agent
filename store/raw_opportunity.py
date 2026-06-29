from datetime import UTC, datetime

from pydantic import BaseModel, Field


class RawOpportunity(BaseModel):
    source: str
    source_url: str
    external_id: str
    company: str
    role_title: str
    location: str
    description_raw: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
