from pyspark.sql import functions as F

from core.store import Store

from foundry.contracts import TRANSFORMATION_SCHEMA


class TransformationRepository:
    def __init__(self, store: Store):
        self.store = store


    def get_transformations(
        self,
        dataclass: str,
        zone: str,
        stage: str,
        sub_stage: str = '',
    ) -> list[dict]:
        config_df = self.store.read(
            table_name='CFG_TRANSFORMATIONS',
            schema=TRANSFORMATION_SCHEMA,
        )

        rows = (
            config_df
            .filter(
                (F.col('dataclass') == dataclass)
                & (F.col('zone') == zone)
                & (F.col('stage') == stage)
                & (F.coalesce(F.col('sub_stage'), F.lit('')) == sub_stage)
                & (F.col('status') == 'A')
            )
            .orderBy('seq')
            .collect()
        )

        return [row.asDict() for row in rows]
