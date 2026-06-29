from enum import Enum


class LifecycleState(str, Enum):
    discovered = "discovered"
    scored = "scored"
    shortlisted = "shortlisted"
    rejected = "rejected"
    drafted = "drafted"                        # TODO Phase 2
    awaiting_approval = "awaiting_approval"    # TODO Phase 2
    approved = "approved"                      # TODO Phase 2
    sent = "sent"                              # TODO Phase 2
    following_up = "following_up"              # TODO Phase 3
    closed = "closed"
