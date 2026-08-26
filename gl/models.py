from dataclasses import dataclass


@dataclass(frozen=True)
class SegmentDefault:
    segment_type: str
    context_type: str
    context_value: str
    default_value: str


@dataclass(frozen=True)
class SegmentResolution:
    segment_type: str
    supplied_value: str | None
    resolved_value: str | None
    defaulted: bool
