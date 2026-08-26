from datetime import date

from registry import RegistryClient, SegmentType

from gl.models import SegmentResolution
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
