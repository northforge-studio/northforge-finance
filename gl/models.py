from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from registry.models import GLSegmentType


@dataclass(frozen=True)
class GLSegments:
    entity_cd: str | None
    branch_cd: str | None
    dept_cd: str | None
    gl_account: str | None
    sub_account: str | None
    affiliate_cd: str | None
    product_cd: str | None
    book_cd: str | None
    source_cd: str | None


@dataclass(frozen=True)
class GLSegmentDefault:
    segment_type: GLSegmentType
    context_type: str
    context_value: str
    default_value: str


@dataclass(frozen=True)
class GLSegmentDefaults:
    values: tuple[GLSegmentDefault, ...]


    def resolve(
        self,
        segment_type: GLSegmentType,
        *,
        entity_cd: str,
    ) -> str | None:
        entity_default = next(
            (
                item.default_value
                for item in self.values
                if item.segment_type == segment_type
                and item.context_type == 'ENTITY_CD'
                and item.context_value == entity_cd
            ),
            None,
        )

        if entity_default is not None:
            return entity_default

        return next(
            (
                item.default_value
                for item in self.values
                if item.segment_type == segment_type
                and item.context_type == 'GLOBAL'
            ),
            None,
        )


@dataclass(frozen=True)
class GLSegmentResolution:
    segment_type: GLSegmentType
    supplied_value: str | None
    resolved_value: str | None
    defaulted: bool


@dataclass(frozen=True)
class GLSegmentResolutions:
    segments: GLSegments | None
    resolutions: tuple[GLSegmentResolution, ...]
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
    src_app_cd: str

    entity_cd: str
    branch_cd: str
    dept_cd: str
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
            branch_cd=self.branch_cd,
            dept_cd=self.dept_cd,
            gl_account=self.gl_account,
            sub_account=self.sub_account,
            affiliate_cd=self.affiliate_cd,
            product_cd=self.product_cd,
            book_cd=self.book_cd,
            source_cd=self.source_cd,
        )


@dataclass(frozen=True)
class GLInstructionValidation:
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class GLPosting:
    gl_posting_id: UUID
    posted_at: datetime

    # lineage
    workflow_run_id: UUID
    producer_run_id: UUID
    dataclass: str
    transaction_number: str
    line_number: str
    foundry_rule_id: str
    posting_id: str
    posting_stream: str
    src_record_id: str
    src_app_cd: str

    # actual posted segments (resolved/defaulted, never the raw Interface values)
    entity_cd: str
    branch_cd: str
    dept_cd: str
    gl_account: str
    sub_account: str
    affiliate_cd: str
    product_cd: str
    book_cd: str
    source_cd: str

    # accounting
    cr_dr_ind: str
    transaction_currency: str
    transaction_amount: Decimal
    accounted_currency: str
    accounted_amount: Decimal
    fx_rate: Decimal
    as_of_date: date
    business_date: date


    @classmethod
    def from_resolution(
        cls,
        instruction: GLInstruction,
        segments: GLSegments,
        *,
        gl_posting_id: UUID,
        posted_at: datetime,
        workflow_run_id: UUID,
        producer_run_id: UUID,
    ) -> 'GLPosting':
        return cls(
            gl_posting_id=gl_posting_id,
            posted_at=posted_at,
            workflow_run_id=workflow_run_id,
            producer_run_id=producer_run_id,
            dataclass=instruction.dataclass,
            transaction_number=instruction.transaction_number,
            line_number=instruction.line_number,
            foundry_rule_id=instruction.foundry_rule_id,
            posting_id=instruction.posting_id,
            posting_stream=instruction.posting_stream,
            src_record_id=instruction.src_record_id,
            src_app_cd=instruction.src_app_cd,
            entity_cd=segments.entity_cd,
            branch_cd=segments.branch_cd,
            dept_cd=segments.dept_cd,
            gl_account=segments.gl_account,
            sub_account=segments.sub_account,
            affiliate_cd=segments.affiliate_cd,
            product_cd=segments.product_cd,
            book_cd=segments.book_cd,
            source_cd=segments.source_cd,
            cr_dr_ind=instruction.cr_dr_ind,
            transaction_currency=instruction.transaction_currency,
            transaction_amount=instruction.transaction_amount,
            accounted_currency=instruction.accounted_currency,
            accounted_amount=instruction.accounted_amount,
            fx_rate=instruction.fx_rate,
            as_of_date=instruction.as_of_date,
            business_date=instruction.business_date,
        )


@dataclass(frozen=True)
class GLRejection:
    gl_rejection_id: UUID
    rejected_at: datetime

    # lineage (enough to trace back to Interface/Foundry; the full
    # instruction remains queryable in interface.trial_balance)
    workflow_run_id: UUID
    producer_run_id: UUID
    dataclass: str
    transaction_number: str
    line_number: str
    foundry_rule_id: str
    posting_id: str
    posting_stream: str
    src_record_id: str
    src_app_cd: str
    business_date: date
    as_of_date: date

    # diagnostics
    rejection_type: str
    rejection_detail: str


    @classmethod
    def from_instruction(
        cls,
        instruction: GLInstruction,
        *,
        gl_rejection_id: UUID,
        rejected_at: datetime,
        rejection_type: str,
        rejection_detail: str,
        workflow_run_id: UUID,
        producer_run_id: UUID,
    ) -> 'GLRejection':
        return cls(
            gl_rejection_id=gl_rejection_id,
            rejected_at=rejected_at,
            workflow_run_id=workflow_run_id,
            producer_run_id=producer_run_id,
            dataclass=instruction.dataclass,
            transaction_number=instruction.transaction_number,
            line_number=instruction.line_number,
            foundry_rule_id=instruction.foundry_rule_id,
            posting_id=instruction.posting_id,
            posting_stream=instruction.posting_stream,
            src_record_id=instruction.src_record_id,
            src_app_cd=instruction.src_app_cd,
            business_date=instruction.business_date,
            as_of_date=instruction.as_of_date,
            rejection_type=rejection_type,
            rejection_detail=rejection_detail,
        )


@dataclass(frozen=True)
class GLInstructionResult:
    posted: bool
    posting: GLPosting | None
    rejection: GLRejection | None
    validation: GLInstructionValidation
    segment_resolution: GLSegmentResolutions | None


@dataclass(frozen=True)
class GLImportResult:
    workflow_run_id: UUID
    producer_run_id: UUID
    source_producer_run_id: UUID
    received_count: int
    posted_count: int
    rejected_count: int
    results: tuple[GLInstructionResult, ...]
