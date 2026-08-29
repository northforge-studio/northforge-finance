from dataclasses import dataclass

from registry import RegistryClient, SegmentType


BREAK_SEGMENTS = {
    SegmentType.ENTITY: 'entity_cd',
    SegmentType.DEPT: 'dept_cd',
    SegmentType.BRANCH: 'branch_cd',
    SegmentType.ACCOUNT: 'gl_account',
    SegmentType.SUB_ACCOUNT: 'sub_account',
    SegmentType.AFFILIATE: 'affiliate_cd',
    SegmentType.PRODUCT: 'product_cd',
    SegmentType.BOOK: 'book_cd',
    SegmentType.SOURCE: 'source_cd',
}


@dataclass(frozen=True)
class SegmentValidationResult:
    segment_type: str
    segment_value: str
    is_valid: bool


class RegistryTools:
    def __init__(
        self, 
        registry_client: RegistryClient
    ):
        self._registry = registry_client


    def validate_segment(
        self,
        segment_type: SegmentType,
        segment_value: str,
    ) -> SegmentValidationResult:
        is_valid = self._registry.validate_segment(
            segment_type,
            segment_value,
        )

        return SegmentValidationResult(
            segment_type=segment_type,
            segment_value=segment_value,
            is_valid=is_valid,
        )
