from pydantic import BaseModel


class SourcePolicyBase(BaseModel):
    policy: str
    enabled: bool
