from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

from core.runs import RunIdentity, RunStatus, ZoneResult
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


class _ReportingPipeline(BasePipeline):
    """A minimal BasePipeline subclass that only implements reporting."""

    def __init__(self, reporting_df, **kwargs):
        super().__init__(**kwargs)
        self._reporting_df = reporting_df
        self.post_reporting_called_with = None


    def pre_staging(self): ...
    def main_staging(self, df): ...
    def post_staging(self, df): ...
    def pre_enrichment(self, source_producer_run_id): ...
    def main_enrichment(self, df): ...
    def post_enrichment(self, df): ...


    def pre_reporting(self, staging_producer_run_id, enrichment_producer_run_id):
        self.pre_reporting_called_with = (
            staging_producer_run_id, enrichment_producer_run_id,
        )
        return self._reporting_df


    def main_reporting(self, df):
        return df


    def post_reporting(self, df):
        self.post_reporting_called_with = df
        return self._config.business_dt


    def pre_posting(self, source_producer_run_id): ...
    def main_posting(self, df): ...
    def post_posting(self, df): ...
    def pre_interface(self, source_producer_run_id): ...
    def main_interface(self, df): ...
    def post_interface(self, df): ...


def _make_pipeline(reporting_df):
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
    )
    return _ReportingPipeline(
        reporting_df=reporting_df,
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
    )


def test_reporting_returns_zone_result_for_supplied_identity(spark):
    df = spark.createDataFrame([(1,), (2,), (3,)], ['ID'])
    pipeline = _make_pipeline(reporting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    staging_producer_run_id = uuid4()
    enrichment_producer_run_id = uuid4()
    result = pipeline.reporting(
        identity,
        staging_producer_run_id=staging_producer_run_id,
        enrichment_producer_run_id=enrichment_producer_run_id,
    )

    assert isinstance(result, ZoneResult)
    assert result.zone == 'REPORTING'
    assert result.status == RunStatus.SUCCEEDED
    assert result.record_count == 3
    assert result.identity == identity

    assert pipeline.post_reporting_called_with is not None
    assert pipeline.post_reporting_called_with.count() == 3


def test_reporting_passes_both_upstream_producer_run_ids_to_pre_reporting(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(reporting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )
    staging_producer_run_id = uuid4()
    enrichment_producer_run_id = uuid4()

    pipeline.reporting(
        identity,
        staging_producer_run_id=staging_producer_run_id,
        enrichment_producer_run_id=enrichment_producer_run_id,
    )

    assert pipeline.pre_reporting_called_with == (
        staging_producer_run_id, enrichment_producer_run_id,
    )


def test_reporting_stamps_supplied_workflow_and_producer_run_id(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(reporting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.reporting(
        identity,
        staging_producer_run_id=uuid4(),
        enrichment_producer_run_id=uuid4(),
    )

    row = pipeline.post_reporting_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)
