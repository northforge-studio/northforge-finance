from datetime import date

from registry import RegistryClient, SegmentType

from gl.models import GLSegmentResolution, GLSegments, SegmentResolution
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
