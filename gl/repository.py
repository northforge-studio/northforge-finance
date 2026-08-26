from pyspark.sql import functions as F

from core.store import Store

from gl.contracts import SEGMENT_DEFAULT_SCHEMA
from gl.models import SegmentDefault


class GLRepository:
    def __init__(self, store: Store):
        self._store = store


    def get_segment_default(
        self,
        segment_type: str,
        context_type: str,
        context_value: str,
    ) -> SegmentDefault | None:
        df = self._store.read(
            table_name='SEGMENT_DEFAULT',
            schema=SEGMENT_DEFAULT_SCHEMA,
        )

        rows = (
            df
            .filter(
                (F.col('SEGMENT_TYPE') == segment_type)
                & (F.col('CONTEXT_TYPE') == context_type)
                & (F.col('CONTEXT_VALUE') == context_value)
            )
            .collect()
        )

        if not rows:
            return None

        row = rows[0]

        return SegmentDefault(
            segment_type=row['SEGMENT_TYPE'],
            context_type=row['CONTEXT_TYPE'],
            context_value=row['CONTEXT_VALUE'],
            default_value=row['DEFAULT_VALUE'],
        )
