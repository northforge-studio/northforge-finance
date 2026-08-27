from datetime import date

from registry import RegistryClient, SegmentType

from gl.models import (
    GLInstruction,
    GLSegmentResolution,
    GLSegments,
    InstructionValidation,
    SegmentResolution,
)
from gl.repository import GLRepository


# Translates GL's own segment_type vocabulary (as used in
# gl.segment_default) to the SegmentType Registry expects for
# validate_segment(...). Every GL segment type is mapped here,
# including ENTITY_CD/SOURCE_CD, so those remain Registry-validated
# like any other segment; they only end up unresolved on an invalid
# value because gl.segment_default has no rows configured for them.
_REGISTRY_SEGMENT_TYPES: dict[str, SegmentType] = {
    'ENTITY_CD': SegmentType.ENTITY,
    'DEPT_CD': SegmentType.DEPARTMENT,
    'BRANCH_CD': SegmentType.BRANCH,
    'GL_ACCOUNT': SegmentType.ACCOUNT,
    'SUB_ACCOUNT': SegmentType.SUB_ACCOUNT,
    'AFFILIATE_CD': SegmentType.AFFILIATE,
    'PRODUCT_CD': SegmentType.PRODUCT,
    'BOOK_CD': SegmentType.BOOK,
    'SOURCE_CD': SegmentType.SOURCE,
}


# Maps each GLSegments field to its segment_type. ENTITY_CD is listed
# first: it is resolved before the rest so its resolved value can be
# used as contextual entity_cd input for the other eight.
_SEGMENT_FIELD_TYPES: tuple[tuple[str, str], ...] = (
    ('entity_cd', 'ENTITY_CD'),
    ('dept_cd', 'DEPT_CD'),
    ('branch_cd', 'BRANCH_CD'),
    ('gl_account', 'GL_ACCOUNT'),
    ('sub_account', 'SUB_ACCOUNT'),
    ('affiliate_cd', 'AFFILIATE_CD'),
    ('product_cd', 'PRODUCT_CD'),
    ('book_cd', 'BOOK_CD'),
    ('source_cd', 'SOURCE_CD'),
)


# Structural requiredness for GLInstruction, in Interface-contract field
# order. "blank" flags None or an empty string; "none" flags only None,
# so a legitimate falsy value (e.g. batch_id=0) is not misreported as
# missing. Matches the actual interface.trial_balance migration, where
# every one of these columns is nullable=False.
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
    ('batch_id', 'MISSING_BATCH_ID', 'none'),
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
        segment_type: str,
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


    def resolve_segment(
        self,
        segment_type: str,
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
            'ENTITY_CD', segments.entity_cd, business_dt=business_dt,
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


    def _is_registry_valid(
        self,
        segment_type: str,
        business_dt: date,
        segment_value: str,
    ) -> bool:
        registry_segment_type = _REGISTRY_SEGMENT_TYPES[segment_type]

        return self._registry.validate_segment(
            registry_segment_type, business_dt, segment_value,
        )
