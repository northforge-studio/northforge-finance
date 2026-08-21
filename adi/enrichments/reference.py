from enum import StrEnum

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from adi.config import REFERENCE_DIR
from adi.contracts import (
    FX_RATE_SCHEMA,
    COUNTERPARTY_SCHEMA,
)


class ReferenceData(StrEnum):
    FX_RATE = 'ref_fx_rate.csv'
    COUNTERPARTY = 'ref_counterparty.csv'


class ReferenceManager:
    REFERENCE_SCHEMAS = {
        ReferenceData.FX_RATE: FX_RATE_SCHEMA,
        ReferenceData.COUNTERPARTY: COUNTERPARTY_SCHEMA,
    }


    def __init__(self, spark: SparkSession):
        self.spark = spark


    def _get_reference_data(
        self,
        reference_data: ReferenceData,
    ) -> DataFrame:
        return (
            self.spark.read
            .option('header', True)
            .option('inferSchema', True)
            .schema(self.REFERENCE_SCHEMAS[reference_data])
            .csv(str(REFERENCE_DIR / reference_data))
        )


    def enrich_fx_rate(self, df: DataFrame) -> DataFrame:
        source_alias = 'source'
        reference_alias = 'reference'

        source_df = df.alias(source_alias)
        reference_df = (
            self._get_reference_data(ReferenceData.FX_RATE)
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
            self._get_reference_data(ReferenceData.COUNTERPARTY)
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
