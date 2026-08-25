from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from core.runs import RunTracker, RunStatus, ExecutionRun
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


class _FullPipeline(BasePipeline):
    """A BasePipeline subclass that captures the DataFrame passed to each
    zone's post_* hook, so stamped run-identity columns can be inspected."""

    def __init__(self, zone_df, **kwargs):
        super().__init__(**kwargs)
        self._zone_df = zone_df
        self.post_staging_called_with = None
        self.post_enrichment_called_with = None
        self.post_reporting_called_with = None
        self.post_posting_called_with = None


    def pre_staging(self):
        return self._zone_df


    def main_staging(self, df):
        return df


    def post_staging(self, df):
        self.post_staging_called_with = df
        return (self._config.business_dt, self._config.batch_id)


    def pre_enrichment(self):
        return self._zone_df


    def main_enrichment(self, df):
        return df


    def post_enrichment(self, df):
        self.post_enrichment_called_with = df
        return (self._config.business_dt, self._config.batch_id)


    def pre_reporting(self):
        return self._zone_df


    def main_reporting(self, df):
        return df


    def post_reporting(self, df):
        self.post_reporting_called_with = df
        return (self._config.business_dt, self._config.batch_id)


    def pre_posting(self):
        return self._zone_df


    def main_posting(self, df):
        return df


    def post_posting(self, df):
        self.post_posting_called_with = df
        return (self._config.business_dt, self._config.batch_id)


def _make_execution_run(**overrides):
    defaults = dict(
        run_id=uuid4(),
        workflow_run_id=uuid4(),
        parent_run_id=None,
        component='FOUNDRY',
        operation='STAGING',
        status=RunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        retry_of_run_id=None,
    )
    defaults.update(overrides)
    return ExecutionRun(**defaults)


def _make_pipeline(zone_df, run_tracker):
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        batch_id='1',
    )
    return _FullPipeline(
        zone_df=zone_df,
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
        run_tracker=run_tracker,
    )


def test_staging_stamps_workflow_and_producer_run_id(spark):
    run_tracker = MagicMock(spec=RunTracker)
    execution_run = _make_execution_run(operation='STAGING')
    run_tracker.start_execution.return_value = execution_run

    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(zone_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()
    pipeline.staging(workflow_run_id=workflow_run_id)

    row = pipeline.post_staging_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(execution_run.run_id)


def test_enrichment_stamps_workflow_and_producer_run_id(spark):
    run_tracker = MagicMock(spec=RunTracker)
    execution_run = _make_execution_run(operation='ENRICHMENT')
    run_tracker.start_execution.return_value = execution_run

    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(zone_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()
    pipeline.enrichment(workflow_run_id=workflow_run_id)

    row = pipeline.post_enrichment_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(execution_run.run_id)


def test_reporting_stamps_workflow_and_producer_run_id(spark):
    run_tracker = MagicMock(spec=RunTracker)
    execution_run = _make_execution_run(operation='REPORTING')
    run_tracker.start_execution.return_value = execution_run

    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(zone_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()
    pipeline.reporting(workflow_run_id=workflow_run_id)

    row = pipeline.post_reporting_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(execution_run.run_id)


def test_posting_stamps_workflow_and_producer_run_id(spark):
    run_tracker = MagicMock(spec=RunTracker)
    execution_run = _make_execution_run(operation='POSTING')
    run_tracker.start_execution.return_value = execution_run

    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(zone_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()
    pipeline.posting(workflow_run_id=workflow_run_id)

    row = pipeline.post_posting_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(execution_run.run_id)


def test_enrichment_overwrites_upstream_producer_run_id(spark):
    run_tracker = MagicMock(spec=RunTracker)
    execution_run = _make_execution_run(operation='ENRICHMENT')
    run_tracker.start_execution.return_value = execution_run

    upstream_workflow_run_id = str(uuid4())
    upstream_producer_run_id = str(uuid4())

    df = spark.createDataFrame(
        [(1, upstream_workflow_run_id, upstream_producer_run_id)],
        ['ID', 'WORKFLOW_RUN_ID', 'PRODUCER_RUN_ID'],
    )
    pipeline = _make_pipeline(zone_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()
    pipeline.enrichment(workflow_run_id=workflow_run_id)

    row = pipeline.post_enrichment_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(execution_run.run_id)
    assert row['PRODUCER_RUN_ID'] != upstream_producer_run_id
