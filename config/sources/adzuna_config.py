from config.sources.base import SourcePolicyBase


class AdzunaConfig(SourcePolicyBase):
    app_id: str = ""
    api_key: str = ""
    location: str = "India"
    max_per_run: int = 50
