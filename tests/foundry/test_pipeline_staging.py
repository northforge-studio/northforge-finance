from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

from core.runs import RunIdentity, RunStatus, ZoneResult
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


class _StagingPipeline(BasePipeline):
    """A minimal BasePipeline subclass that only implements staging."""

    def __init__(self, staging_df, **kwargs):
        super().__init__(**kwargs)
        self._staging_df = staging_df
        self.post_staging_called_with = None


    def pre_staging(self):
        return self._staging_df


    def main_staging(self, df):
        return df


    def post_staging(self, df):
        self.post_staging_called_with = df
        return self._config.business_dt


    def pre_enrichment(self, source_producer_run_id): ...
    def main_enrichment(self, df): ...
    def post_enrichment(self, df): ...
    def pre_reporting(self, staging_producer_run_id, enrichment_producer_run_id): ...
    def main_reporting(self, df): ...
    def post_reporting(self, df): ...
    def pre_posting(self, source_producer_run_id): ...
    def main_posting(self, df): ...
    def post_posting(self, df): ...
    def pre_interface(self, source_producer_run_id): ...
    def main_interface(self, df): ...
    def post_interface(self, df): ...


def _make_pipeline(staging_df):
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
    )
    return _StagingPipeline(
        staging_df=staging_df,
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
    )


def test_staging_returns_zone_result_for_supplied_identity(spark):
    df = spark.createDataFrame([(1,), (2,), (3,)], ['ID'])
    pipeline = _make_pipeline(staging_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    result = pipeline.staging(identity)

    assert isinstance(result, ZoneResult)
    assert result.zone == 'STAGING'
    assert result.status == RunStatus.SUCCEEDED
    assert result.record_count == 3
    assert result.identity == identity

    assert pipeline.post_staging_called_with is not None
    assert pipeline.post_staging_called_with.count() == 3


def test_staging_stamps_supplied_workflow_and_producer_run_id(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(staging_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=None,
    )

    pipeline.staging(identity)

    row = pipeline.post_staging_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)


def test_staging_overwrites_any_preexisting_run_identity_columns(spark):
    upstream_workflow_run_id = str(uuid4())
    upstream_producer_run_id = str(uuid4())

    df = spark.createDataFrame(
        [(1, upstream_workflow_run_id, upstream_producer_run_id)],
        ['ID', 'WORKFLOW_RUN_ID', 'PRODUCER_RUN_ID'],
    )
    pipeline = _make_pipeline(staging_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=None,
    )

    pipeline.staging(identity)

    row = pipeline.post_staging_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)
    assert row['PRODUCER_RUN_ID'] != upstream_producer_run_id
