from datetime import date
from uuid import UUID

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from core.store import Store

from foundry.contracts import (
    TRIAL_BALANCE_SOURCE_SCHEMA,
    TRIAL_BALANCE_STAGING_SCHEMA,
    TRIAL_BALANCE_ENRICHMENT_SCHEMA,
    TRIAL_BALANCE_REPORTING_SCHEMA,
    TRIAL_BALANCE_POSTING_SCHEMA,
    TRIAL_BALANCE_INTERFACE_SCHEMA,
)


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


    def read_staging(self, producer_run_id: UUID) -> DataFrame:
        staging_df = self.store.read(
            table_name='TRIAL_BALANCE_STAGING',
            schema=TRIAL_BALANCE_STAGING_SCHEMA,
        ).filter(F.col('PRODUCER_RUN_ID') == str(producer_run_id))

        if staging_df.isEmpty():
            raise ValueError(f"No staging data found for producer run: {producer_run_id}")

        return staging_df


    def read_enrichment(self, producer_run_id: UUID) -> DataFrame:
        enrichment_df = self.store.read(
            table_name='TRIAL_BALANCE_ENRICHMENT',
            schema=TRIAL_BALANCE_ENRICHMENT_SCHEMA,
        ).filter(F.col('PRODUCER_RUN_ID') == str(producer_run_id))

        if enrichment_df.isEmpty():
            raise ValueError(f"No enrichment data found for producer run: {producer_run_id}")

        return enrichment_df


    def read_reporting(self, producer_run_id: UUID) -> DataFrame:
        reporting_df = self.store.read(
            table_name='TRIAL_BALANCE_REPORTING',
            schema=TRIAL_BALANCE_REPORTING_SCHEMA,
        ).filter(F.col('PRODUCER_RUN_ID') == str(producer_run_id))

        if reporting_df.isEmpty():
            raise ValueError(f"No reporting data found for producer run: {producer_run_id}")

        return reporting_df


    def read_posting(self, producer_run_id: UUID) -> DataFrame:
        posting_df = self.store.read(
            table_name='TRIAL_BALANCE_POSTING',
            schema=TRIAL_BALANCE_POSTING_SCHEMA,
        ).filter(F.col('PRODUCER_RUN_ID') == str(producer_run_id))

        if posting_df.isEmpty():
            raise ValueError(f"No posting data found for producer run: {producer_run_id}")

        return posting_df


    def read_interface(self, producer_run_id: UUID) -> DataFrame:
        interface_df = self.store.read(
            table_name='TRIAL_BALANCE_INTERFACE',
            schema=TRIAL_BALANCE_INTERFACE_SCHEMA,
        ).filter(F.col('PRODUCER_RUN_ID') == str(producer_run_id))

        if interface_df.isEmpty():
            raise ValueError(f"No interface data found for producer run: {producer_run_id}")

        return interface_df


    def write_staging(self, df: DataFrame) -> None:
        self.store.write(
            df,
            table_name='TRIAL_BALANCE_STAGING',
        )


    def write_enrichment(self, df: DataFrame) -> None:
        self.store.write(
            df,
            table_name='TRIAL_BALANCE_ENRICHMENT',
        )


    def write_reporting(self, df: DataFrame) -> None:
        self.store.write(
            df,
            table_name='TRIAL_BALANCE_REPORTING',
        )


    def write_posting(self, df: DataFrame) -> None:
        self.store.write(
            df,
            table_name='TRIAL_BALANCE_POSTING',
        )


    def write_interface(self, df: DataFrame) -> None:
        self.store.write(
            df,
            table_name='TRIAL_BALANCE_INTERFACE',
        )


    def delete_staging(self, producer_run_id: UUID) -> None:
        self.store.delete(
            table_name='TRIAL_BALANCE_STAGING',
            filters={'PRODUCER_RUN_ID': str(producer_run_id)},
            schema=TRIAL_BALANCE_STAGING_SCHEMA,
        )


    def delete_enrichment(self, producer_run_id: UUID) -> None:
        self.store.delete(
            table_name='TRIAL_BALANCE_ENRICHMENT',
            filters={'PRODUCER_RUN_ID': str(producer_run_id)},
            schema=TRIAL_BALANCE_ENRICHMENT_SCHEMA,
        )


    def delete_reporting(self, producer_run_id: UUID) -> None:
        self.store.delete(
            table_name='TRIAL_BALANCE_REPORTING',
            filters={'PRODUCER_RUN_ID': str(producer_run_id)},
            schema=TRIAL_BALANCE_REPORTING_SCHEMA,
        )


    def delete_posting(self, producer_run_id: UUID) -> None:
        self.store.delete(
            table_name='TRIAL_BALANCE_POSTING',
            filters={'PRODUCER_RUN_ID': str(producer_run_id)},
            schema=TRIAL_BALANCE_POSTING_SCHEMA,
        )


    def delete_interface(self, producer_run_id: UUID) -> None:
        self.store.delete(
            table_name='TRIAL_BALANCE_INTERFACE',
            filters={'PRODUCER_RUN_ID': str(producer_run_id)},
            schema=TRIAL_BALANCE_INTERFACE_SCHEMA,
        )
