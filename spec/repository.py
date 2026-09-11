from pyspark.sql import functions as F

from core.store import Store

from spec.models import SpecType
from spec.contracts import TRANSFORMATION_SCHEMA, FILE_LAYOUT_SCHEMA


class SpecRepository:
    def __init__(self, store: Store):
        self._store = store


    def get_transformations(
        self,
        dataclass: str,
        zone: str,
        stage: str,
        sub_stage: str = '',
    ) -> list[dict]:
        config_df = self._store.read(
            table_name=SpecType.TRANSFORMATION,
            schema=TRANSFORMATION_SCHEMA,
        )

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


    def get_file_layout_expressions(
        self,
        dataclass: str,
    ) -> list[str]:
        layout_df = self._store.read(
            table_name=SpecType.FILE_LAYOUT,
            schema=FILE_LAYOUT_SCHEMA,
        )

        rows = (
            layout_df
            .filter(
                F.col('DATACLASS') == dataclass
            )
            .orderBy('SEQ')
            .collect()
        )

        if not rows:
            raise KeyError(
                f'File layout not found for '
                f'DATACLASS={dataclass!r}'
            )

        expressions = []

        for row in rows:
            expression = ''
            if row['EXPRESSION'] != '':
                expression = row['EXPRESSION']
            else:
                expression = row['POSTING_ATTRIBUTE_NAME']

            expression = f'{expression} AS {row["GL_ATTRIBUTE_NAME"]}'
            expressions.append(expression)

        return expressions
