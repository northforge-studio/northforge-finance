from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from adi.pipeline.base import BasePipeline
from adi.contracts import TRIAL_BALANCE_STAGING_SCHEMA
from adi.enrichments import (
    TransformationManager, 
    ReferenceManager
)

from finmap import FinMapClient


class TrialBalancePipeline(BasePipeline):
    DATACLASS = 'TRIAL_BALANCE'


    def __init__(
        self,
        transformation_manager: TransformationManager,
        reference_manager: ReferenceManager,
        finmap: FinMapClient,
    ):
        self._transformation_manager = transformation_manager
        self._reference_manager = reference_manager
        self._finmap = finmap


    def pre_staging(self, df: DataFrame) -> DataFrame:
        df = self._add_row_id(df)

        df = self._transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='pre',
        )

        df = self._finmap.apply(df, mapping_name='ENTITY_MAPPING')
        df = self._finmap.apply(df, mapping_name='MEASURE_TYPE_MAPPING')

        df = self._reference_manager.enrich_fx_rate(df)
        df = self._reference_manager.enrich_counterparty(df)

        return df


    def main_staging(self, df: DataFrame) -> DataFrame:
        df = self._transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='main',
        )
        
        return df


    def post_staging(self, df: DataFrame) -> DataFrame:
        df = self._get_total_acct_func_amt(df)

        df = self._transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='post',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_STAGING_SCHEMA)

        return df


    def pre_enrichment(self, df: DataFrame) -> DataFrame:
        gateway_rules = self._finmap.get_rule_config(self.DATACLASS)

        return self._execute_rules(df, gateway_rules)


    def _get_total_acct_func_amt(self, df: DataFrame) -> DataFrame:
        account_window = Window.partitionBy('SRC_ACCOUNT_ID')

        return df.withColumn(
            'TOTAL_ACCT_FUNC_AMT',
            F.sum('POSTING_MEASURE_FUNC_AMT')
            .over(account_window)
            .cast('decimal(28,12)'),
        )
