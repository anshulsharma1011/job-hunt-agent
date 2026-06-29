from pydantic import BaseModel


class MatchingConfig(BaseModel):
    score_threshold: int
    max_per_cycle: int
    max_concurrent_scoring: int
