from pyspark.sql import functions as F

from core.store import Store


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
        config_df = self.store.read(table_name='CFG_TRANSFORMATIONS')

        rows = (
            config_df
            .filter(
                (F.col('DATACLASS') == dataclass)
                & (F.col('ZONE') == zone)
                & (F.col('STAGE') == stage)
                & (F.coalesce(F.col('SUB_STAGE'), F.lit('')) == sub_stage)
                & (F.col('STATUS') == 'A')
            )
            .orderBy('SEQ')
            .collect()
        )

        return [row.asDict() for row in rows]
