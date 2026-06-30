from pydantic import BaseModel


class AppSection(BaseModel):
    name: str
    env: str
    resume_path: str = "materials/resume.pdf"
