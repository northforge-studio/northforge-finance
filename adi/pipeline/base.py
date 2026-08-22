from datetime import date
from abc import ABC, abstractmethod

from pyspark.sql import DataFrame, Column
from pyspark.sql import functions as F
from pyspark.sql.types import StructType

from adi.rules import (
    PostingRuleProcessor,
    GatewayRuleProcessor,
    RuleExecutionEngine
)
from adi.enrichments import (
    TransformationManager, 
    ReferenceManager
)
from adi.models import PipelineConfig

from finmap import FinMapClient, GatewayRule


class BasePipeline(ABC):
    def __init__(
        self,
        config: PipelineConfig,
        finmap: FinMapClient,
        reference_manager: ReferenceManager,
        transformation_manager: TransformationManager,
    ):  
        self._config = config
        self._finmap = finmap
        self._reference_manager = reference_manager
        self._transformation_manager = transformation_manager

        posting_rule_processor = PostingRuleProcessor(
            dataclass=config.dataclass,
            transformation_manager=transformation_manager,
            finmap=finmap
        )
        gateway_rule_processor = GatewayRuleProcessor(
            posting_rule_processor=posting_rule_processor,
            transformation_manager=transformation_manager,
            finmap=finmap
        )
        self._rule_execution_engine = RuleExecutionEngine(
            gateway_rule_processor=gateway_rule_processor
        )


    def run(self) -> tuple[date, str]:
        try:
            self.staging()
            self.enrichment()
            self.reporting()
        except Exception:
            self.rollback()
            raise

        return tuple([self._config.business_dt, self._config.batch_id])


    def staging(self) -> tuple[date, str]:
        df = self.pre_staging()
        df = self.main_staging(df)
        self.post_staging(df)

        return tuple([self._config.business_dt, self._config.batch_id])


    def enrichment(self) -> tuple[date, str]:
        df = self.pre_enrichment()
        df = self.main_enrichment(df)
        self.post_enrichment(df)

        return tuple([self._config.business_dt, self._config.batch_id])


    def reporting(self) -> tuple[date, str]:
        df = self.pre_reporting()
        df = self.main_reporting(df)
        self.post_reporting(df)

        return tuple([self._config.business_dt, self._config.batch_id])


    def posting(self, df: DataFrame) -> tuple[date, str]:
        df = self.pre_posting(df)
        df = self.main_posting(df)
        self.post_posting(df)

        return tuple([self._config.business_dt, self._config.batch_id])


    @abstractmethod
    def pre_staging(self) -> DataFrame:
        ...


    @abstractmethod
    def main_staging(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_staging(self, df: DataFrame) -> tuple[date, str]:
        ...


    @abstractmethod
    def pre_enrichment(self) -> DataFrame:
        ...


    @abstractmethod
    def main_enrichment(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_enrichment(self, df: DataFrame) -> tuple[date, str]:
        ...


    @abstractmethod
    def pre_reporting(self) -> DataFrame:
        ...


    @abstractmethod
    def main_reporting(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_reporting(self, df: DataFrame) -> tuple[date, str]:
        ...


    def rollback(self) -> None:
        pass


    def _add_row_id(self, df: DataFrame) -> DataFrame:
        return (
            df.coalesce(1)
            .withColumn(
                'ROW_ID', 
                (F.monotonically_increasing_id() + 1).cast('string')
            )
        )


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


    def _execute_rules(
        self, 
        df: DataFrame, 
        gateway_rules: list[GatewayRule]
    ) -> DataFrame:

        return self._rule_execution_engine.execute(df, gateway_rules)


    @staticmethod
    def _numeric_id(column: str) -> Column:
        return F.regexp_extract(column, r'(\d+)$', 1).cast('int')
