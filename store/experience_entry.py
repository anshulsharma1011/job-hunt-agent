from pydantic import BaseModel


class ExperienceEntry(BaseModel):
    company: str
    role: str
    years: float
    highlights: list[str]
