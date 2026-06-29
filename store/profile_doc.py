from datetime import datetime

from pydantic import BaseModel, Field

from store.experience_entry import ExperienceEntry
from store.search_criteria import SearchCriteria


class ProfileDoc(BaseModel):
    profile_id: str
    version: int
    created_at: datetime
    is_active: bool = True
    personal: dict
    skills: list[str]
    experience_years: float
    seniority: str
    experience: list[ExperienceEntry]
    preferences: SearchCriteria
    writing_samples: list[str] = Field(default_factory=list)
    source_files: list[str]
