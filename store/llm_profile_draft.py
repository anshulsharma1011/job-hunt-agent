from pydantic import BaseModel, Field

from store.experience_entry import ExperienceEntry
from store.search_criteria import SearchCriteria


class LLMProfileDraft(BaseModel):
    """LLM-extractable fields from a resume. System fields (profile_id, version, etc.) are added by ProfileAgent."""
    personal: dict[str, object]
    skills: list[str]
    experience_years: float
    seniority: str
    experience: list[ExperienceEntry]
    preferences: SearchCriteria
    writing_samples: list[str] = Field(default_factory=list)
