from typing import Optional

from pydantic import BaseModel, Field


class SourcePolicyConfig(BaseModel):
    policy: str
    enabled: bool
    companies: list[str] = Field(default_factory=list)
    max_per_run: Optional[int] = None
    max_requests_per_cycle: Optional[int] = None
    location: Optional[str] = None
    app_id: Optional[str] = None
    api_key: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
