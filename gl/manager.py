from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from pyspark.sql import DataFrame

from registry import RegistryClient
from registry.models import SegmentType

from core.runs.models import RunIdentity

from gl.models import (
    GLSegments,
    GLPosting,
    GLRejection,
    GLInstruction,
    GLImportResult,
    SegmentDefaults,
    SegmentResolution,
    GLInstructionResult,
    GLSegmentResolution,
    InstructionValidation,
)
from gl.repository import GLRepository


# Maps each GLSegments field to its segment_type. ENTITY is listed
# first: it is resolved before the rest so its resolved value can be
# used as contextual entity_cd input for the other eight.
_SEGMENT_FIELD_TYPES: tuple[tuple[str, SegmentType], ...] = (
    ('entity_cd', SegmentType.ENTITY),
    ('branch_cd', SegmentType.BRANCH),
    ('dept_cd', SegmentType.DEPARTMENT),
    ('gl_account', SegmentType.ACCOUNT),
    ('sub_account', SegmentType.SUB_ACCOUNT),
    ('affiliate_cd', SegmentType.AFFILIATE),
    ('product_cd', SegmentType.PRODUCT),
    ('book_cd', SegmentType.BOOK),
    ('source_cd', SegmentType.SOURCE),
)


# Structural requiredness for GLInstruction, in Interface-contract field
# order. "blank" flags None or an empty string; "none" flags only None,
# so a legitimate falsy value (e.g. transaction_amount=0) is not
# misreported as missing. Matches the actual interface.trial_balance
# migration, where every one of these columns is nullable=False.
_REQUIRED_INSTRUCTION_FIELDS: tuple[tuple[str, str, str], ...] = (
    ('workflow_run_id', 'MISSING_WORKFLOW_RUN_ID', 'none'),
    ('producer_run_id', 'MISSING_PRODUCER_RUN_ID', 'none'),
    ('dataclass', 'MISSING_DATACLASS', 'blank'),
    ('transaction_number', 'MISSING_TRANSACTION_NUMBER', 'blank'),
    ('line_number', 'MISSING_LINE_NUMBER', 'blank'),
    ('foundry_rule_id', 'MISSING_FOUNDRY_RULE_ID', 'blank'),
    ('posting_id', 'MISSING_POSTING_ID', 'blank'),
    ('posting_stream', 'MISSING_POSTING_STREAM', 'blank'),
    ('src_record_id', 'MISSING_SRC_RECORD_ID', 'blank'),
    ('src_app_cd', 'MISSING_SRC_APP_CD', 'blank'),
    ('transaction_currency', 'MISSING_TRANSACTION_CURRENCY', 'blank'),
    ('transaction_amount', 'MISSING_TRANSACTION_AMOUNT', 'none'),
    ('accounted_currency', 'MISSING_ACCOUNTED_CURRENCY', 'blank'),
    ('accounted_amount', 'MISSING_ACCOUNTED_AMOUNT', 'none'),
    ('fx_rate', 'MISSING_FX_RATE', 'none'),
    ('as_of_date', 'MISSING_AS_OF_DATE', 'none'),
    ('business_date', 'MISSING_BUSINESS_DATE', 'none'),
)

_VALID_CR_DR_VALUES = frozenset({'DR', 'CR'})


class GLManager:
    def __init__(self, repository: GLRepository, registry: RegistryClient):
        self._repository = repository
        self._registry = registry


    def get_segment_default(
        self,
        segment_type: SegmentType,
        *,
        entity_cd: str | None = None,
    ) -> str | None:
        if entity_cd is not None:
            contextual = self._repository.get_segment_default(
                segment_type, 'ENTITY_CD', entity_cd,
            )
            if contextual is not None:
                return contextual.default_value

        global_default = self._repository.get_segment_default(
            segment_type, '*', '*',
        )
        if global_default is not None:
            return global_default.default_value

        return None


    def get_segment_defaults(self) -> SegmentDefaults:
        return SegmentDefaults(
            values=self._repository.get_segment_defaults(),
        )


    def resolve_segment(
        self,
        segment_type: SegmentType,
        segment_value: str | None,
        *,
        business_dt: date,
        entity_cd: str | None = None,
    ) -> SegmentResolution:
        if segment_value and self._is_registry_valid(
            segment_type, business_dt, segment_value,
        ):
            return SegmentResolution(
                segment_type=segment_type,
                supplied_value=segment_value,
                resolved_value=segment_value,
                defaulted=False,
            )

        default_value = self.get_segment_default(segment_type, entity_cd=entity_cd)

        if default_value is not None and self._is_registry_valid(
            segment_type, business_dt, default_value,
        ):
            return SegmentResolution(
                segment_type=segment_type,
                supplied_value=segment_value,
                resolved_value=default_value,
                defaulted=True,
            )

        return SegmentResolution(
            segment_type=segment_type,
            supplied_value=segment_value,
            resolved_value=None,
            defaulted=False,
        )


    def resolve_segments(
        self,
        segments: GLSegments,
        *,
        business_dt: date,
    ) -> GLSegmentResolution:
        entity_resolution = self.resolve_segment(
            SegmentType.ENTITY, segments.entity_cd, business_dt=business_dt,
        )

        if entity_resolution.resolved_value is None:
            return GLSegmentResolution(
                segments=None,
                resolutions=(entity_resolution,),
                resolved=False,
            )

        entity_cd = entity_resolution.resolved_value
        resolutions = [entity_resolution]

        for field, segment_type in _SEGMENT_FIELD_TYPES[1:]:
            resolutions.append(
                self.resolve_segment(
                    segment_type,
                    getattr(segments, field),
                    business_dt=business_dt,
                    entity_cd=entity_cd,
                )
            )

        if any(resolution.resolved_value is None for resolution in resolutions):
            return GLSegmentResolution(
                segments=None,
                resolutions=tuple(resolutions),
                resolved=False,
            )

        final_segments = GLSegments(**{
            field: resolution.resolved_value
            for (field, _), resolution in zip(_SEGMENT_FIELD_TYPES, resolutions)
        })

        return GLSegmentResolution(
            segments=final_segments,
            resolutions=tuple(resolutions),
            resolved=True,
        )


    def validate_instruction(
        self,
        instruction: GLInstruction,
    ) -> InstructionValidation:
        errors: list[str] = []

        for field, error_code, check in _REQUIRED_INSTRUCTION_FIELDS:
            value = getattr(instruction, field)
            is_missing = value is None if check == 'none' else not value
            if is_missing:
                errors.append(error_code)

        if instruction.cr_dr_ind not in _VALID_CR_DR_VALUES:
            errors.append('INVALID_CR_DR_IND')

        return InstructionValidation(valid=not errors, errors=tuple(errors))


    def process_instruction(
        self,
        instruction: GLInstruction,
        *,
        identity: RunIdentity | None = None,
        gl_posting_id: UUID | None = None,
        posted_at: datetime | None = None,
        gl_rejection_id: UUID | None = None,
        rejected_at: datetime | None = None,
    ) -> GLInstructionResult:
        # GL's own execution lineage, when known, is what gets stamped onto
        # output rows. Absent an orchestrated identity (e.g. ad hoc/direct
        # calls), fall back to the instruction's own lineage.
        workflow_run_id = (
            identity.workflow_run_id if identity is not None
            else instruction.workflow_run_id
        )
        producer_run_id = (
            identity.run_id if identity is not None
            else instruction.producer_run_id
        )

        validation = self.validate_instruction(instruction)

        if not validation.valid:
            rejection = self._reject(
                instruction,
                rejection_type='STRUCTURAL_VALIDATION',
                rejection_detail=','.join(validation.errors),
                gl_rejection_id=gl_rejection_id,
                rejected_at=rejected_at,
                workflow_run_id=workflow_run_id,
                producer_run_id=producer_run_id,
            )
            return GLInstructionResult(
                posted=False,
                posting=None,
                rejection=rejection,
                validation=validation,
                segment_resolution=None,
            )

        segment_resolution = self.resolve_segments(
            instruction.to_segments(),
            business_dt=instruction.business_date,
        )

        if not segment_resolution.resolved:
            unresolved = ','.join(
                resolution.segment_type.field_name.upper()
                for resolution in segment_resolution.resolutions
                if resolution.resolved_value is None
            )
            rejection = self._reject(
                instruction,
                rejection_type='SEGMENT_RESOLUTION',
                rejection_detail=unresolved,
                gl_rejection_id=gl_rejection_id,
                rejected_at=rejected_at,
                workflow_run_id=workflow_run_id,
                producer_run_id=producer_run_id,
            )
            return GLInstructionResult(
                posted=False,
                posting=None,
                rejection=rejection,
                validation=validation,
                segment_resolution=segment_resolution,
            )

        posting = GLPosting.from_resolution(
            instruction,
            segment_resolution.segments,
            gl_posting_id=gl_posting_id or uuid4(),
            posted_at=posted_at or datetime.now(timezone.utc),
            workflow_run_id=workflow_run_id,
            producer_run_id=producer_run_id,
        )
        self._repository.write_posting(posting)

        return GLInstructionResult(
            posted=True,
            posting=posting,
            rejection=None,
            validation=validation,
            segment_resolution=segment_resolution,
        )


    def import_instructions(
        self,
        identity: RunIdentity,
        source_producer_run_id: UUID,
    ) -> GLImportResult:
        # V1 invariant: one Interface producer execution per workflow, so
        # workflow_run_id alone is sufficient to select GL's source rows.
        # source_producer_run_id is retained purely as the exact Interface
        # execution's lineage, stamped onto the result below.
        instructions = self._repository.get_instructions(
            workflow_run_id=identity.workflow_run_id,
        )

        results = tuple(
            self.process_instruction(instruction, identity=identity)
            for instruction in instructions
        )

        posted_count = sum(1 for result in results if result.posted)

        return GLImportResult(
            workflow_run_id=identity.workflow_run_id,
            producer_run_id=identity.run_id,
            source_producer_run_id=source_producer_run_id,
            received_count=len(results),
            posted_count=posted_count,
            rejected_count=len(results) - posted_count,
            results=results,
        )


    def rollback_execution(self, identity: RunIdentity) -> None:
        self._repository.delete_postings(identity.workflow_run_id)
        self._repository.delete_rejections(identity.workflow_run_id)


    def get_postings(self, workflow_run_id: UUID) -> DataFrame:
        return self._repository.get_postings(workflow_run_id)


    def get_rejections(self, workflow_run_id: UUID) -> DataFrame:
        return self._repository.get_rejections(workflow_run_id)


    def _reject(
        self,
        instruction: GLInstruction,
        *,
        rejection_type: str,
        rejection_detail: str,
        gl_rejection_id: UUID | None,
        rejected_at: datetime | None,
        workflow_run_id: UUID,
        producer_run_id: UUID,
    ) -> GLRejection:
        rejection = GLRejection.from_instruction(
            instruction,
            gl_rejection_id=gl_rejection_id or uuid4(),
            rejected_at=rejected_at or datetime.now(timezone.utc),
            rejection_type=rejection_type,
            rejection_detail=rejection_detail,
            workflow_run_id=workflow_run_id,
            producer_run_id=producer_run_id,
        )
        self._repository.write_rejection(rejection)

        return rejection


    def _is_registry_valid(
        self,
        segment_type: SegmentType,
        business_dt: date,
        segment_value: str,
    ) -> bool:
        return self._registry.validate_segment(
            segment_type, business_dt, segment_value,
        )
