from enum import Enum


class RecommendedTrack(str, Enum):
    apply = "apply"
    outreach = "outreach"
    skip = "skip"
