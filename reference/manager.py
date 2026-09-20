from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from reference.models import ReferenceData
from reference.repository import ReferenceRepository


class ReferenceManager:
    def __init__(self, repository: ReferenceRepository):
        self._repository = repository


    def enrich_reference_data(self, df: DataFrame, reference_data: ReferenceData) -> DataFrame:
        if reference_data == ReferenceData.FX_RATE:
            return self._enrich_fx_rate(df)
        if reference_data == ReferenceData.COUNTERPARTY:
            return self._enrich_counterparty(df)
        else:
            raise ValueError(f'Unsupported reference data: {reference_data}')


    def _enrich_fx_rate(self, df: DataFrame) -> DataFrame:
        source_alias = 'source'
        reference_alias = 'reference'

        source_df = df.alias(source_alias)
        reference_df = (
            self._repository.get_reference_data(ReferenceData.FX_RATE)
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


    def _enrich_counterparty(self, df: DataFrame) -> DataFrame:
        source_alias = 'source'
        reference_alias = 'reference'

        source_df = df.alias(source_alias)
        reference_df = (
            self._repository.get_reference_data(ReferenceData.COUNTERPARTY)
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
