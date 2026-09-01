from abc import ABC, abstractmethod
from uuid import UUID

from pyspark.sql import DataFrame, Column
from pyspark.sql import functions as F
from pyspark.sql.types import StructType

from foundry.rules import (
    PostingRuleProcessor,
    GatewayRuleProcessor,
    RuleExecutionEngine
)
from foundry.models import PipelineConfig

from atlas import AtlasClient
from atlas.models import GatewayRule
from reference import ReferenceClient
from spec import SpecClient
from core.runs.models import RunIdentity, ZoneResult, RunStatus


class BasePipeline(ABC):
    def __init__(
        self,
        config: PipelineConfig,
        atlas: AtlasClient,
        reference: ReferenceClient,
        spec: SpecClient,
    ):
        self._config = config
        self._atlas = atlas
        self._reference = reference
        self._spec = spec

        posting_rule_processor = PostingRuleProcessor(
            dataclass=config.dataclass,
            spec=spec,
            atlas=atlas
        )
        gateway_rule_processor = GatewayRuleProcessor(
            posting_rule_processor=posting_rule_processor,
            spec=spec,
            atlas=atlas
        )
        self._rule_execution_engine = RuleExecutionEngine(
            gateway_rule_processor=gateway_rule_processor
        )


    @property
    def config(self) -> PipelineConfig:
        return self._config


    def staging(self, identity: RunIdentity) -> ZoneResult:
        df = self.pre_staging()
        df = self.main_staging(df)
        df = self._stamp_run_identity(df, identity)
        self.post_staging(df)

        record_count = df.count()

        return ZoneResult(
            identity=identity,
            zone='STAGING',
            status=RunStatus.SUCCEEDED,
            record_count=record_count,
        )


    def enrichment(
        self,
        identity: RunIdentity,
    ) -> ZoneResult:
        df = self.pre_enrichment(identity.workflow_run_id)
        df = self.main_enrichment(df)
        df = self._stamp_run_identity(df, identity)
        self.post_enrichment(df)

        record_count = df.count()

        return ZoneResult(
            identity=identity,
            zone='ENRICHMENT',
            status=RunStatus.SUCCEEDED,
            record_count=record_count,
        )


    def reporting(
        self,
        identity: RunIdentity,
    ) -> ZoneResult:
        df = self.pre_reporting(identity.workflow_run_id)
        df = self.main_reporting(df)
        df = self._stamp_run_identity(df, identity)
        self.post_reporting(df)

        record_count = df.count()

        return ZoneResult(
            identity=identity,
            zone='REPORTING',
            status=RunStatus.SUCCEEDED,
            record_count=record_count,
        )


    def posting(
        self,
        identity: RunIdentity,
    ) -> ZoneResult:
        df = self.pre_posting(identity.workflow_run_id)
        df = self.main_posting(df)
        df = self._stamp_run_identity(df, identity)
        self.post_posting(df)

        record_count = df.count()

        return ZoneResult(
            identity=identity,
            zone='POSTING',
            status=RunStatus.SUCCEEDED,
            record_count=record_count,
        )


    def interface(
        self,
        identity: RunIdentity,
    ) -> ZoneResult:
        df = self.pre_interface(identity.workflow_run_id)
        df = self.main_interface(df)
        df = self._stamp_run_identity(df, identity)
        self.post_interface(df)

        record_count = df.count()

        return ZoneResult(
            identity=identity,
            zone='INTERFACE',
            status=RunStatus.SUCCEEDED,
            record_count=record_count,
        )


    @abstractmethod
    def pre_staging(self) -> DataFrame:
        ...


    @abstractmethod
    def main_staging(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_staging(self, df: DataFrame) -> None:
        ...


    @abstractmethod
    def pre_enrichment(self, workflow_run_id: UUID) -> DataFrame:
        ...


    @abstractmethod
    def main_enrichment(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_enrichment(self, df: DataFrame) -> None:
        ...


    @abstractmethod
    def pre_reporting(self, workflow_run_id: UUID) -> DataFrame:
        ...


    @abstractmethod
    def main_reporting(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_reporting(self, df: DataFrame) -> None:
        ...


    @abstractmethod
    def pre_posting(self, workflow_run_id: UUID) -> DataFrame:
        ...


    @abstractmethod
    def main_posting(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_posting(self, df: DataFrame) -> None:
        ...


    @abstractmethod
    def pre_interface(self, workflow_run_id: UUID) -> DataFrame:
        ...


    @abstractmethod
    def main_interface(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_interface(self, df: DataFrame) -> None:
        ...


    def rollback_execution(self, operation: str, identity: RunIdentity) -> None:
        pass


    def _stamp_run_identity(
        self,
        df: DataFrame,
        identity: RunIdentity,
    ) -> DataFrame:
        return (
            df
            .withColumn('WORKFLOW_RUN_ID', F.lit(str(identity.workflow_run_id)))
            .withColumn('PRODUCER_RUN_ID', F.lit(str(identity.run_id)))
        )


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
