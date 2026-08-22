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

from finmap import FinMapClient, GatewayRule


class BasePipeline(ABC):
    def __init__(
        self,
        dataclass: str,
        transformation_manager: TransformationManager,
        reference_manager: ReferenceManager,
        finmap: FinMapClient,
    ):  
        self._dataclass = dataclass
        self._transformation_manager = transformation_manager
        self._reference_manager = reference_manager
        self._finmap = finmap

        posting_rule_processor = PostingRuleProcessor(
            dataclass=dataclass,
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


    def run(self, df: DataFrame) -> DataFrame:
        df = self.staging(df)
        df = self.enrichment(df)
        df = self.posting(df)

        return df


    def staging(self, df: DataFrame) -> DataFrame:
        df = self.pre_staging(df)
        df = self.main_staging(df)
        df = self.post_staging(df)

        return df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            self._numeric_id('STAGING_ID')
        )


    def enrichment(self, df: DataFrame) -> DataFrame:
        df = self.pre_enrichment(df)
        df = self.main_enrichment(df)
        df = self.post_enrichment(df)

        return df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            self._numeric_id('STAGING_ID'),
            self._numeric_id('ENRICHMENT_ID')
        )


    def posting(self, df: DataFrame) -> DataFrame:
        df = self.pre_posting(df)
        df = self.main_posting(df)
        df = self.post_posting(df)

        return df


    @abstractmethod
    def pre_staging(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def main_staging(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_staging(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def pre_enrichment(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def main_enrichment(self, df: DataFrame) -> DataFrame:
        return df


    @abstractmethod
    def post_enrichment(self, df: DataFrame) -> DataFrame:
        return df


    def pre_posting(self, df: DataFrame) -> DataFrame:
        return df


    def main_posting(self, df: DataFrame) -> DataFrame:
        return df


    def post_posting(self, df: DataFrame) -> DataFrame:
        return df


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
