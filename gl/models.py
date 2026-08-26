from dataclasses import dataclass


@dataclass(frozen=True)
class SegmentDefault:
    segment_type: str
    context_type: str
    context_value: str
    default_value: str
