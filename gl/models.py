from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


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


@dataclass(frozen=True)
class GLInstruction:
    workflow_run_id: UUID
    producer_run_id: UUID
    dataclass: str
    transaction_number: str
    line_number: str
    foundry_rule_id: str
    posting_id: str
    posting_stream: str
    src_record_id: str
    batch_id: int
    src_app_cd: str

    entity_cd: str
    dept_cd: str
    branch_cd: str
    gl_account: str
    sub_account: str
    affiliate_cd: str
    product_cd: str
    book_cd: str
    source_cd: str

    cr_dr_ind: str
    transaction_currency: str
    transaction_amount: Decimal
    accounted_currency: str
    accounted_amount: Decimal
    fx_rate: Decimal
    as_of_date: date
    business_date: date


    def to_segments(self) -> GLSegments:
        return GLSegments(
            entity_cd=self.entity_cd,
            dept_cd=self.dept_cd,
            branch_cd=self.branch_cd,
            gl_account=self.gl_account,
            sub_account=self.sub_account,
            affiliate_cd=self.affiliate_cd,
            product_cd=self.product_cd,
            book_cd=self.book_cd,
            source_cd=self.source_cd,
        )


@dataclass(frozen=True)
class InstructionValidation:
    valid: bool
    errors: tuple[str, ...]
