from pyspark.sql import DataFrame

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
        self.transformation_manager = transformation_manager
        self.reference_manager = reference_manager
        self.finmap = finmap


    def pre_staging(self, df: DataFrame) -> DataFrame:
        df = self.transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='pre',
        )

        df = self.finmap.apply(df, mapping_name='ENTITY_MAPPING')
        df = self.finmap.apply(df, mapping_name='MEASURE_TYPE_MAPPING')

        df = self.reference_manager.enrich_fx_rate(df)
        df = self.reference_manager.enrich_counterparty(df)

        return df


    def main_staging(self, df: DataFrame) -> DataFrame:
        df = self.transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='main',
        )
        
        return df


    def post_staging(self, df: DataFrame) -> DataFrame:
        df = self.transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='post',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_STAGING_SCHEMA)

        return df
