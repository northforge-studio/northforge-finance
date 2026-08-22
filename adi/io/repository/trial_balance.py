from datetime import date

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from adi.contracts import (
    TRIAL_BALANCE_SOURCE_SCHEMA,
    TRIAL_BALANCE_STAGING_SCHEMA,
)
from adi.io.store import Store


class TrialBalanceRepository:
    def __init__(self, store: Store):
        self.store = store


    def read_source(self, business_dt: date) -> DataFrame:
        source_df = self.store.read(
            table_name='TRIAL_BALANCE_SOURCE',
            schema=TRIAL_BALANCE_SOURCE_SCHEMA,
        ).filter(F.col('BUSINESS_DT') == business_dt)

        if source_df.isEmpty():
            raise ValueError(f"No source data found for business date: {business_dt}")
        
        return source_df


    def read_staging(self, business_dt: date, batch_id: str) -> DataFrame:
        staging_df = self.store.read(
            table_name='TRIAL_BALANCE_STAGING',
            schema=TRIAL_BALANCE_STAGING_SCHEMA,
        ).filter(
            (F.col('BUSINESS_DT') == business_dt) & (F.col('BATCH_ID') == batch_id)
        )

        if staging_df.isEmpty():
            raise ValueError(f"No staging data found for business date: {business_dt} and batch ID: {batch_id}")
        
        return staging_df


    def write_staging(self, df: DataFrame) -> None:
        self.store.write(
            df,
            table_name='TRIAL_BALANCE_STAGING',
        )


    def get_next_batch_id(self, business_dt: date) -> int:
        staging_df = self.store.read(
            table_name='TRIAL_BALANCE_STAGING',
            schema=TRIAL_BALANCE_STAGING_SCHEMA,
        )

        max_batch_id = (
            staging_df
            .filter(F.col('BUSINESS_DT') == business_dt)
            .agg(F.max('BATCH_ID').alias('MAX_BATCH_ID'))
            .collect()[0]['MAX_BATCH_ID']
        )

        return (max_batch_id or 0) + 1
