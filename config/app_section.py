from pydantic import BaseModel


class AppSection(BaseModel):
    name: str
    env: str
