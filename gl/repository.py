from core.db import PostgresConfig, PostgresExecutor

from gl.models import SegmentDefault


class GLRepository:
    def __init__(self):
        self._config = PostgresConfig.from_env()
        self._executor = PostgresExecutor(self._config)


    def get_segment_default(
        self,
        segment_type: str,
        context_type: str,
        context_value: str,
    ) -> SegmentDefault | None:
        row = self._executor.fetch_one(
            '''
            SELECT segment_type, context_type, context_value, default_value
            FROM gl.segments_default
            WHERE segment_type = :segment_type
              AND context_type = :context_type
              AND context_value = :context_value
            ''',
            {
                'segment_type': segment_type,
                'context_type': context_type,
                'context_value': context_value,
            },
        )

        if row is None:
            return None

        return SegmentDefault(
            segment_type=row['segment_type'],
            context_type=row['context_type'],
            context_value=row['context_value'],
            default_value=row['default_value'],
        )
