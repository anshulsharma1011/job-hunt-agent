from pydantic import BaseModel


class LogConfig(BaseModel):
    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: str = "output/logs"
