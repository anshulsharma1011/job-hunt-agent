from enum import Enum


class SourcePolicy(str, Enum):
    allowed = "allowed"
    human_assisted = "human-assisted"
    blocked = "blocked"
