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


@dataclass(frozen=True)
class GLSegments:
    entity_cd: str | None
    dept_cd: str | None
    branch_cd: str | None
    gl_account: str | None
    sub_account: str | None
    affiliate_cd: str | None
    product_cd: str | None
    book_cd: str | None
    source_cd: str | None


@dataclass(frozen=True)
class GLSegmentResolution:
    segments: GLSegments | None
    resolutions: tuple[SegmentResolution, ...]
    resolved: bool
