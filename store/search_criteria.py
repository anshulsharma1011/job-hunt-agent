from pydantic import BaseModel, Field


class SearchCriteria(BaseModel):
    titles: list[str]
    locations: list[str]
    remote: bool
    comp_min_lpa: int | None = None
    company_stages: list[str] = Field(default_factory=list)
    exclusion_keywords: list[str] = Field(default_factory=list)
    score_threshold: int = 70
