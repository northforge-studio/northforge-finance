from pyspark.sql import DataFrame
from pyspark.sql.types import StructType

from adi.contracts import TRIAL_BALANCE_STAGING_SCHEMA
from adi.enrichments import (
    TransformationManager, 
    ReferenceManager
)

from finmap import FinMapClient


class TrialBalancePipeline:
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

    def staging(self, df: DataFrame) -> DataFrame:
        df = self.transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='pre',
        )

        df = self.finmap.apply(
            df,
            mapping_name='ENTITY_MAPPING',
        )

        df = self.reference_manager.enrich_fx_rate(df)
        df = self.reference_manager.enrich_counterparty(df)

        df = self.transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='main',
        )

        df = self.finmap.apply(
            df,
            mapping_name='MEASURE_TYPE_MAPPING',
        )

        df = self.transformation_manager.apply(
            df=df,
            dataclass=self.DATACLASS,
            zone='staging',
            stage='post',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_STAGING_SCHEMA)

        return df
    

    def _align_to_schema(
        self,
        df: DataFrame,
        schema: StructType,
    ) -> DataFrame:
        columns = [
            field.name
            for field in schema.fields
        ]

        return df.select(*columns)
