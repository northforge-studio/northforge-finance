from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from reference.repository import Repository


class ReferenceManager:
    def __init__(self, repository: Repository):
        self.repository = repository


    def enrich_fx_rate(self, df: DataFrame) -> DataFrame:
        source_alias = 'source'
        reference_alias = 'reference'

        source_df = df.alias(source_alias)
        reference_df = (
            self.repository.get_fx_rate()
            .alias(reference_alias)
        )

        source_cols = [f'{source_alias}.{col}' for col in source_df.columns]
        reference_cols = [f'{reference_alias}.FX_RATE']

        condition = (
            (F.col(f'{source_alias}.POSTING_MEASURE_CCY_CD') == F.col(f'{reference_alias}.FROM_CURRENCY'))
            & (F.col(f'{source_alias}.POSTING_MEASURE_FUNC_CCY_CD') == F.col(f'{reference_alias}.TO_CURRENCY'))
        )

        joined_df = source_df.join(
            reference_df,
            on=condition,
            how='left'
        )

        return joined_df.select(
            *source_cols,
            *reference_cols
        )


    def enrich_counterparty(self, df: DataFrame) -> DataFrame:
        source_alias = 'source'
        reference_alias = 'reference'

        source_df = df.alias(source_alias)
        reference_df = (
            self.repository.get_counterparty()
            .alias(reference_alias)
        )

        source_cols = [f'{source_alias}.{col}' for col in source_df.columns]
        reference_cols = [f'{reference_alias}.CLIENT_ID_TYPE']

        condition = (
            F.coalesce(
                F.col(f'{source_alias}.CPTY_REF_ID').cast('string'),
                F.lit(''),
            )
            ==
            F.coalesce(
                F.col(f'{reference_alias}.CPTY_REF_ID').cast('string'),
                F.lit(''),
            )
        )


        joined_df = source_df.join(
            reference_df,
            on=condition,
            how='left'
        )

        return joined_df.select(
            *source_cols,
            *reference_cols
        )
