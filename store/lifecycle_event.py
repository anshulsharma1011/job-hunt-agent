from datetime import UTC, datetime

from pydantic import BaseModel, Field

from store.lifecycle_state import LifecycleState


class LifecycleEvent(BaseModel):
    state: LifecycleState
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))
