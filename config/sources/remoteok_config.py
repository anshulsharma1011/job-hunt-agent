from config.sources.base import SourcePolicyBase


class RemoteOKConfig(SourcePolicyBase):
    max_per_run: int = 50
