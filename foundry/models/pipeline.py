from datetime import date
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    dataclass: str
    business_dt: date
