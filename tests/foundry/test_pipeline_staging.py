from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from core.runs import RunTracker, RunStatus, ZoneResult, ExecutionRun
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


class _StagingPipeline(BasePipeline):
    """A minimal BasePipeline subclass that only implements staging."""

    def __init__(self, staging_df, raise_error=False, **kwargs):
        super().__init__(**kwargs)
        self._staging_df = staging_df
        self._raise_error = raise_error
        self.post_staging_called_with = None


    def pre_staging(self):
        if self._raise_error:
            raise ValueError('boom')
        return self._staging_df


    def main_staging(self, df):
        return df


    def post_staging(self, df):
        self.post_staging_called_with = df
        return (self._config.business_dt, self._config.batch_id)


    def pre_enrichment(self): ...
    def main_enrichment(self, df): ...
    def post_enrichment(self, df): ...
    def pre_reporting(self): ...
    def main_reporting(self, df): ...
    def post_reporting(self, df): ...
    def pre_posting(self): ...
    def main_posting(self, df): ...
    def post_posting(self, df): ...
    def pre_interface(self): ...
    def main_interface(self, df): ...
    def post_interface(self, df): ...


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


def _make_pipeline(staging_df, run_tracker, raise_error=False):
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        batch_id='1',
    )
    return _StagingPipeline(
        staging_df=staging_df,
        raise_error=raise_error,
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
        run_tracker=run_tracker,
    )


def test_staging_returns_zone_result_and_completes_execution(spark):
    run_tracker = MagicMock(spec=RunTracker)
    execution_run = _make_execution_run()
    run_tracker.start_execution.return_value = execution_run

    df = spark.createDataFrame([(1,), (2,), (3,)], ['ID'])
    pipeline = _make_pipeline(staging_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()

    result = pipeline.staging(workflow_run_id=workflow_run_id)

    assert isinstance(result, ZoneResult)
    assert result.zone == 'STAGING'
    assert result.status == RunStatus.SUCCEEDED
    assert result.record_count == 3
    assert result.identity.workflow_run_id == workflow_run_id
    assert result.identity.run_id == execution_run.run_id
    assert result.identity.parent_run_id is None

    run_tracker.start_execution.assert_called_once_with(
        workflow_run_id=workflow_run_id,
        component='FOUNDRY',
        operation='STAGING',
        parent_run_id=None,
    )
    run_tracker.complete_execution.assert_called_once_with(execution_run.run_id)
    run_tracker.fail_execution.assert_not_called()

    assert pipeline.post_staging_called_with is not None
    assert pipeline.post_staging_called_with.count() == 3


def test_staging_passes_parent_run_id_through(spark):
    run_tracker = MagicMock(spec=RunTracker)
    execution_run = _make_execution_run()
    run_tracker.start_execution.return_value = execution_run

    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(staging_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()
    parent_run_id = uuid4()

    result = pipeline.staging(
        workflow_run_id=workflow_run_id,
        parent_run_id=parent_run_id,
    )

    run_tracker.start_execution.assert_called_once_with(
        workflow_run_id=workflow_run_id,
        component='FOUNDRY',
        operation='STAGING',
        parent_run_id=parent_run_id,
    )
    assert result.identity.parent_run_id == parent_run_id


def test_staging_fails_execution_and_reraises_on_error(spark):
    run_tracker = MagicMock(spec=RunTracker)
    execution_run = _make_execution_run()
    run_tracker.start_execution.return_value = execution_run

    pipeline = _make_pipeline(
        staging_df=None,
        run_tracker=run_tracker,
        raise_error=True,
    )

    workflow_run_id = uuid4()

    with pytest.raises(ValueError, match='boom'):
        pipeline.staging(workflow_run_id=workflow_run_id)

    run_tracker.fail_execution.assert_called_once_with(execution_run.run_id)
    run_tracker.complete_execution.assert_not_called()
