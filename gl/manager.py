from gl.repository import GLRepository


class GLManager:
    def __init__(self, repository: GLRepository):
        self._repository = repository


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
