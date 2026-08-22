from datetime import date

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from adi.pipeline.base import BasePipeline
from adi.contracts import (
    TRIAL_BALANCE_STAGING_SCHEMA,
    TRIAL_BALANCE_ENRICHMENT_SCHEMA,
    TRIAL_BALANCE_REPORTING_SCHEMA,
)
from adi.enrichments import (
    TransformationManager, 
    ReferenceManager
)
from adi.models import PipelineConfig
from adi.io import TrialBalanceRepository

from finmap import FinMapClient


class TrialBalancePipeline(BasePipeline):
    DATACLASS = 'TRIAL_BALANCE'


    def __init__(
        self,
        business_dt: date,
        finmap: FinMapClient,
        repository: TrialBalanceRepository,
        reference_manager: ReferenceManager,
        transformation_manager: TransformationManager,
    ):
        config = PipelineConfig(
            dataclass=self.DATACLASS,
            business_dt=business_dt
        )
        super().__init__(
            config = config,
            finmap = finmap,
            reference_manager = reference_manager,
            transformation_manager = transformation_manager
        )
        self._finmap = finmap
        self._repository = repository
        self._reference_manager = reference_manager
        self._transformation_manager = transformation_manager


    def pre_staging(self) -> DataFrame:
        df = self._repository.read_source(
            business_dt=self._config.business_dt
        )

        df = self._resolve_batch_id(df)

        df = self._transformation_manager.apply(
            df,
            dataclass=self.DATACLASS,
            zone='STG',
            stage='PRE',
        )

        df = self._finmap.apply(df, mapping_name='ENTITY_MAPPING')
        df = self._finmap.apply(df, mapping_name='MEASURE_TYPE_MAPPING')

        df = self._reference_manager.enrich_fx_rate(df)
        df = self._reference_manager.enrich_counterparty(df)

        return df


    def main_staging(self, df: DataFrame) -> DataFrame:
        df = self._transformation_manager.apply(
            df,
            dataclass=self.DATACLASS,
            zone='STG',
            stage='MAIN',
        )
        
        return df


    def post_staging(self, df: DataFrame) -> tuple[date, str]:
        df = self._add_row_id(df)
        df = self._get_total_acct_func_amt(df)

        df = self._transformation_manager.apply(
            df,
            dataclass=self.DATACLASS,
            zone='STG',
            stage='POST',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_STAGING_SCHEMA)
        df = df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            self._numeric_id('STAGING_ID')
        )

        self._repository.write_staging(df)

        return tuple([self._config.business_dt, self._config.batch_id])


    def pre_enrichment(self) -> DataFrame:
        df = self._repository.read_staging(
            business_dt=self._config.business_dt,
            batch_id=self._config.batch_id
        )

        gateway_rules = self._finmap.get_rule_config(self.DATACLASS)

        return self._execute_rules(df, gateway_rules)


    def main_enrichment(self, df: DataFrame) -> DataFrame:
        return df


    def post_enrichment(self, df: DataFrame) -> tuple[date, str]:
        df = self._add_row_id(df)

        df = self._transformation_manager.apply(
            df,
            dataclass=self.DATACLASS,
            zone='ENR',
            stage='POST',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_ENRICHMENT_SCHEMA)
        df = df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            self._numeric_id('STAGING_ID'),
            self._numeric_id('ENRICHMENT_ID'),
        )

        self._repository.write_enrichment(df)

        return tuple([self._config.business_dt, self._config.batch_id])


    def pre_reporting(self) -> DataFrame:
        staging_df = self._repository.read_staging(
            business_dt=self._config.business_dt,
            batch_id=self._config.batch_id,
        )
        enrichment_df = self._repository.read_enrichment(
            business_dt=self._config.business_dt,
            batch_id=self._config.batch_id,
        )

        return self._combine_staging_and_enrichment(staging_df, enrichment_df)


    def main_reporting(self, df: DataFrame) -> DataFrame:
        df = self._transformation_manager.apply(
            df,
            dataclass=self.DATACLASS,
            zone='RPT',
            stage='MAIN',
        )

        return df


    def post_reporting(self, df: DataFrame) -> tuple[date, str]:
        df = self._add_row_id(df)

        df = self._transformation_manager.apply(
            df,
            dataclass=self.DATACLASS,
            zone='RPT',
            stage='POST',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_REPORTING_SCHEMA)
        df = df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            self._numeric_id('STAGING_ID'),
            self._numeric_id('ENRICHMENT_ID'),
            self._numeric_id('REPORTING_ID'),
        )

        self._repository.write_reporting(df)

        return tuple([self._config.business_dt, self._config.batch_id])


    def rollback(self) -> None:
        business_dt = self._config.business_dt
        batch_id = self._config.batch_id

        if batch_id is None:
            return

        self._repository.delete_staging(business_dt, batch_id)
        self._repository.delete_enrichment(business_dt, batch_id)
        self._repository.delete_reporting(business_dt, batch_id)


    def _combine_staging_and_enrichment(
        self,
        staging_df: DataFrame,
        enrichment_df: DataFrame,
    ) -> DataFrame:
        enrichment_only_columns = [
            field.name
            for field in TRIAL_BALANCE_ENRICHMENT_SCHEMA.fields
            if field.name not in {f.name for f in TRIAL_BALANCE_STAGING_SCHEMA.fields}
        ]

        unprocessed_staging_df = staging_df.join(
            enrichment_df.select('STAGING_ID'),
            on='STAGING_ID',
            how='left_anti',
        )

        for column in enrichment_only_columns:
            unprocessed_staging_df = unprocessed_staging_df.withColumn(
                column, F.lit('')
            )

        return enrichment_df.unionByName(unprocessed_staging_df)


    def _resolve_batch_id(self, df: DataFrame) -> DataFrame:
        batch_id = self._repository.get_next_batch_id(self._config.business_dt)
        self._config.batch_id = batch_id

        return df.withColumn('BATCH_ID', F.lit(batch_id))


    def _get_total_acct_func_amt(self, df: DataFrame) -> DataFrame:
        account_window = Window.partitionBy('SRC_ACCOUNT_ID')

        return df.withColumn(
            'TOTAL_ACCT_FUNC_AMT',
            F.sum('POSTING_MEASURE_FUNC_AMT')
            .over(account_window)
            .cast('decimal(28,12)'),
        )
