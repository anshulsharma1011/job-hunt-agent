from config.sources.base import SourcePolicyBase


class LinkedInConfig(SourcePolicyBase):
    max_requests_per_cycle: int = 5
