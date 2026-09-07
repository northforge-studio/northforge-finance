from datetime import date

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from core.store import Store

from registry.contracts import (
    SEGMENT_SCHEMAS,
    SEGMENT_CODE_COLUMNS,
)
from registry.models import GLSegmentType


class RegistryRepository:
    def __init__(self, store: Store):
        self._store = store


    def get_segment(
        self,
        segment: GLSegmentType,
        business_dt: date,
        segment_cd: str,
    ) -> DataFrame:
        if segment not in SEGMENT_SCHEMAS:
            raise ValueError(f"Unsupported segment: {segment}")

        schema = SEGMENT_SCHEMAS[segment]
        code_column = SEGMENT_CODE_COLUMNS[segment]

        df = self._store.read(
            table_name=segment,
            schema=schema,
        )

        return df.filter(
            (F.col('BUSINESS_DT') == business_dt)
            & (F.col(code_column) == segment_cd)
            & (F.col('STATUS') == 'A')
        )
