from pydantic import BaseModel


class OutputConfig(BaseModel):
    report_dir: str
    report_format: str
