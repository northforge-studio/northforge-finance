from datetime import date
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
from foundry.enrichments import TransformationManager
from foundry.models import PipelineConfig

from atlas import AtlasClient, GatewayRule
from reference import ReferenceClient
from core.runs import RunTracker, RunIdentity, ZoneResult, PipelineResult, RunStatus


class BasePipeline(ABC):
    def __init__(
        self,
        config: PipelineConfig,
        atlas: AtlasClient,
        reference: ReferenceClient,
        transformation_manager: TransformationManager,
        run_tracker: RunTracker,
    ):
        self._config = config
        self._atlas = atlas
        self._reference = reference
        self._transformation_manager = transformation_manager
        self._run_tracker = run_tracker

        posting_rule_processor = PostingRuleProcessor(
            dataclass=config.dataclass,
            transformation_manager=transformation_manager,
            atlas=atlas
        )
        gateway_rule_processor = GatewayRuleProcessor(
            posting_rule_processor=posting_rule_processor,
            transformation_manager=transformation_manager,
            atlas=atlas
        )
        self._rule_execution_engine = RuleExecutionEngine(
            gateway_rule_processor=gateway_rule_processor
        )


    def run(self, workflow_run_id: UUID) -> PipelineResult:
        pipeline_execution = self._run_tracker.start_execution(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation='PIPELINE',
        )

        try:
            staging_result = self.staging(
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
            )
        except Exception:
            self._run_tracker.fail_execution(pipeline_execution.run_id)
            raise

        self._run_tracker.complete_execution(pipeline_execution.run_id)

        return PipelineResult(
            identity=RunIdentity(
                workflow_run_id=workflow_run_id,
                run_id=pipeline_execution.run_id,
                parent_run_id=pipeline_execution.parent_run_id,
            ),
            status=RunStatus.SUCCEEDED,
            zones=(staging_result,),
        )


    def staging(
        self,
        *,
        workflow_run_id: UUID,
        parent_run_id: UUID | None = None,
    ) -> ZoneResult:
        execution_run = self._run_tracker.start_execution(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation='STAGING',
            parent_run_id=parent_run_id,
        )

        try:
            df = self.pre_staging()
            df = self.main_staging(df)
            self.post_staging(df)

            record_count = df.count()
        except Exception:
            self._run_tracker.fail_execution(execution_run.run_id)
            raise

        self._run_tracker.complete_execution(execution_run.run_id)

        return ZoneResult(
            identity=RunIdentity(
                workflow_run_id=workflow_run_id,
                run_id=execution_run.run_id,
                parent_run_id=parent_run_id,
            ),
            zone='STAGING',
            status=RunStatus.SUCCEEDED,
            record_count=record_count,
        )


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


    def posting(self) -> tuple[date, str]:
        df = self.pre_posting()
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


    @abstractmethod
    def pre_posting(self) -> DataFrame:
        ...


    @abstractmethod
    def main_posting(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_posting(self, df: DataFrame) -> tuple[date, str]:
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
