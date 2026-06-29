from pydantic import BaseModel, Field

from store.lifecycle_state import LifecycleState
from store.recommended_track import RecommendedTrack
from store.lifecycle_event import LifecycleEvent
from store.raw_opportunity import RawOpportunity


class ScoredOpportunity(BaseModel):
    opportunity_id: str
    cycle_id: str
    raw: RawOpportunity
    score: int
    fit_rationale: list[str]
    red_flags: list[str]
    recommended_track: RecommendedTrack
    lifecycle_state: LifecycleState
    history: list[LifecycleEvent] = Field(default_factory=list)
