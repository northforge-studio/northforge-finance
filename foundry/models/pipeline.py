from dataclasses import dataclass
from datetime import date


@dataclass
class PipelineConfig:
    dataclass: str
    business_dt: date
