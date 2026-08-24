from datetime import date, datetime, timezone
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest

from core.runs import RunTracker, RunStatus, PipelineResult, ExecutionRun
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


class _StagingPipeline(BasePipeline):
    """A minimal BasePipeline subclass that only implements staging."""

    def __init__(self, staging_df, raise_error=False, **kwargs):
        super().__init__(**kwargs)
        self._staging_df = staging_df
        self._raise_error = raise_error


    def pre_staging(self):
        if self._raise_error:
            raise ValueError('boom')
        return self._staging_df


    def main_staging(self, df):
        return df


    def post_staging(self, df):
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


def _make_execution_run(**overrides):
    defaults = dict(
        run_id=uuid4(),
        workflow_run_id=uuid4(),
        parent_run_id=None,
        component='FOUNDRY',
        operation='PIPELINE',
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
        transformation_manager=MagicMock(),
        run_tracker=run_tracker,
    )


def test_run_starts_pipeline_execution_and_passes_it_as_staging_parent(spark):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    staging_execution = _make_execution_run(operation='STAGING')
    run_tracker.start_execution.side_effect = [pipeline_execution, staging_execution]

    df = spark.createDataFrame([(1,), (2,)], ['ID'])
    pipeline = _make_pipeline(staging_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()

    pipeline.run(workflow_run_id=workflow_run_id)

    assert run_tracker.start_execution.call_args_list == [
        call(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation='PIPELINE',
        ),
        call(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation='STAGING',
            parent_run_id=pipeline_execution.run_id,
        ),
    ]


def test_run_returns_pipeline_result_with_staging_zone(spark):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    staging_execution = _make_execution_run(operation='STAGING')
    run_tracker.start_execution.side_effect = [pipeline_execution, staging_execution]

    df = spark.createDataFrame([(1,), (2,), (3,)], ['ID'])
    pipeline = _make_pipeline(staging_df=df, run_tracker=run_tracker)

    workflow_run_id = uuid4()

    result = pipeline.run(workflow_run_id=workflow_run_id)

    assert isinstance(result, PipelineResult)
    assert result.status == RunStatus.SUCCEEDED
    assert result.identity.workflow_run_id == workflow_run_id
    assert result.identity.run_id == pipeline_execution.run_id
    assert result.identity.parent_run_id is None

    assert len(result.zones) == 1
    staging_result = result.zones[0]
    assert staging_result.zone == 'STAGING'
    assert staging_result.status == RunStatus.SUCCEEDED
    assert staging_result.record_count == 3
    assert staging_result.identity.run_id == staging_execution.run_id
    assert staging_result.identity.parent_run_id == pipeline_execution.run_id


def test_run_completes_pipeline_execution_on_success(spark):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    staging_execution = _make_execution_run(operation='STAGING')
    run_tracker.start_execution.side_effect = [pipeline_execution, staging_execution]

    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(staging_df=df, run_tracker=run_tracker)

    pipeline.run(workflow_run_id=uuid4())

    run_tracker.complete_execution.assert_any_call(staging_execution.run_id)
    run_tracker.complete_execution.assert_any_call(pipeline_execution.run_id)
    assert run_tracker.complete_execution.call_count == 2
    run_tracker.fail_execution.assert_not_called()


def test_run_fails_pipeline_execution_and_reraises_when_staging_fails(spark):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    staging_execution = _make_execution_run(operation='STAGING')
    run_tracker.start_execution.side_effect = [pipeline_execution, staging_execution]

    pipeline = _make_pipeline(
        staging_df=None,
        run_tracker=run_tracker,
        raise_error=True,
    )

    with pytest.raises(ValueError, match='boom'):
        pipeline.run(workflow_run_id=uuid4())

    run_tracker.fail_execution.assert_any_call(staging_execution.run_id)
    run_tracker.fail_execution.assert_any_call(pipeline_execution.run_id)
    assert run_tracker.fail_execution.call_count == 2
    run_tracker.complete_execution.assert_not_called()
