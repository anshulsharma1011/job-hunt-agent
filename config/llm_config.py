from pydantic import BaseModel


class LLMConfig(BaseModel):
    model: str
    base_url: str
    timeout_seconds: int
    token_budget_per_cycle: int
