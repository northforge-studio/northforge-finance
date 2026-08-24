from datetime import date, datetime, timezone
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest

from core.runs import RunTracker, RunStatus, PipelineResult, ExecutionRun
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


ZONES = ('staging', 'enrichment', 'reporting', 'posting')


class _FullPipeline(BasePipeline):
    """A BasePipeline subclass implementing all four zones, each backed
    by a caller-supplied DataFrame. `raise_error_in` names a single zone
    whose `pre_*` hook should raise instead of returning data."""

    def __init__(
        self,
        zone_dfs,
        raise_error_in=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._zone_dfs = zone_dfs
        self._raise_error_in = raise_error_in


    def _pre(self, zone):
        if self._raise_error_in == zone:
            raise ValueError('boom')
        return self._zone_dfs.get(zone)


    def _post(self, df):
        return (self._config.business_dt, self._config.batch_id)


    def pre_staging(self): return self._pre('staging')
    def main_staging(self, df): return df
    def post_staging(self, df): return self._post(df)

    def pre_enrichment(self): return self._pre('enrichment')
    def main_enrichment(self, df): return df
    def post_enrichment(self, df): return self._post(df)

    def pre_reporting(self): return self._pre('reporting')
    def main_reporting(self, df): return df
    def post_reporting(self, df): return self._post(df)

    def pre_posting(self): return self._pre('posting')
    def main_posting(self, df): return df
    def post_posting(self, df): return self._post(df)


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


def _make_pipeline(zone_dfs, run_tracker, raise_error_in=None):
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        batch_id='1',
    )
    return _FullPipeline(
        zone_dfs=zone_dfs,
        raise_error_in=raise_error_in,
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        transformation_manager=MagicMock(),
        run_tracker=run_tracker,
    )


def _make_zone_executions():
    return {
        zone: _make_execution_run(operation=zone.upper())
        for zone in ZONES
    }


def test_run_starts_pipeline_execution_and_passes_it_as_parent_to_all_zones(spark):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    zone_executions = _make_zone_executions()
    run_tracker.start_execution.side_effect = [
        pipeline_execution,
        *[zone_executions[zone] for zone in ZONES],
    ]

    zone_dfs = {
        zone: spark.createDataFrame([(1,)], ['ID'])
        for zone in ZONES
    }
    pipeline = _make_pipeline(zone_dfs=zone_dfs, run_tracker=run_tracker)

    workflow_run_id = uuid4()

    pipeline.run(workflow_run_id=workflow_run_id)

    assert run_tracker.start_execution.call_args_list == [
        call(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation='PIPELINE',
        ),
        *[
            call(
                workflow_run_id=workflow_run_id,
                component='FOUNDRY',
                operation=zone.upper(),
                parent_run_id=pipeline_execution.run_id,
            )
            for zone in ZONES
        ],
    ]


def test_run_returns_pipeline_result_with_all_zones_in_order(spark):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    zone_executions = _make_zone_executions()
    run_tracker.start_execution.side_effect = [
        pipeline_execution,
        *[zone_executions[zone] for zone in ZONES],
    ]

    zone_dfs = {
        'staging': spark.createDataFrame([(1,), (2,), (3,)], ['ID']),
        'enrichment': spark.createDataFrame([(1,), (2,)], ['ID']),
        'reporting': spark.createDataFrame([(1,)], ['ID']),
        'posting': spark.createDataFrame([(1,), (2,), (3,), (4,)], ['ID']),
    }
    pipeline = _make_pipeline(zone_dfs=zone_dfs, run_tracker=run_tracker)

    workflow_run_id = uuid4()

    result = pipeline.run(workflow_run_id=workflow_run_id)

    assert isinstance(result, PipelineResult)
    assert result.status == RunStatus.SUCCEEDED
    assert result.identity.workflow_run_id == workflow_run_id
    assert result.identity.run_id == pipeline_execution.run_id
    assert result.identity.parent_run_id is None

    assert len(result.zones) == 4
    assert [z.zone for z in result.zones] == [
        'STAGING', 'ENRICHMENT', 'REPORTING', 'POSTING',
    ]

    expected_record_counts = {
        'STAGING': 3,
        'ENRICHMENT': 2,
        'REPORTING': 1,
        'POSTING': 4,
    }
    for zone_result in result.zones:
        assert zone_result.status == RunStatus.SUCCEEDED
        assert zone_result.record_count == expected_record_counts[zone_result.zone]
        assert zone_result.identity.parent_run_id == pipeline_execution.run_id
        assert zone_result.identity.run_id == zone_executions[zone_result.zone.lower()].run_id


def test_run_completes_pipeline_execution_on_success(spark):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    zone_executions = _make_zone_executions()
    run_tracker.start_execution.side_effect = [
        pipeline_execution,
        *[zone_executions[zone] for zone in ZONES],
    ]

    zone_dfs = {
        zone: spark.createDataFrame([(1,)], ['ID'])
        for zone in ZONES
    }
    pipeline = _make_pipeline(zone_dfs=zone_dfs, run_tracker=run_tracker)

    pipeline.run(workflow_run_id=uuid4())

    for zone in ZONES:
        run_tracker.complete_execution.assert_any_call(zone_executions[zone].run_id)
    run_tracker.complete_execution.assert_any_call(pipeline_execution.run_id)
    assert run_tracker.complete_execution.call_count == 5
    run_tracker.fail_execution.assert_not_called()


def test_run_creates_dependencies_between_consecutive_zones(spark):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    zone_executions = _make_zone_executions()
    run_tracker.start_execution.side_effect = [
        pipeline_execution,
        *[zone_executions[zone] for zone in ZONES],
    ]

    zone_dfs = {
        zone: spark.createDataFrame([(1,)], ['ID'])
        for zone in ZONES
    }
    pipeline = _make_pipeline(zone_dfs=zone_dfs, run_tracker=run_tracker)

    pipeline.run(workflow_run_id=uuid4())

    assert run_tracker.add_dependency.call_args_list == [
        call(
            consumer_run_id=zone_executions['enrichment'].run_id,
            producer_run_id=zone_executions['staging'].run_id,
            input_role='STAGING',
        ),
        call(
            consumer_run_id=zone_executions['reporting'].run_id,
            producer_run_id=zone_executions['enrichment'].run_id,
            input_role='ENRICHMENT',
        ),
        call(
            consumer_run_id=zone_executions['posting'].run_id,
            producer_run_id=zone_executions['reporting'].run_id,
            input_role='REPORTING',
        ),
    ]


@pytest.mark.parametrize('failing_zone', ZONES)
def test_run_fails_pipeline_execution_and_reraises_when_a_zone_fails(spark, failing_zone):
    run_tracker = MagicMock(spec=RunTracker)
    pipeline_execution = _make_execution_run()
    zone_executions = _make_zone_executions()

    zones_up_to_failure = ZONES[:ZONES.index(failing_zone) + 1]
    run_tracker.start_execution.side_effect = [
        pipeline_execution,
        *[zone_executions[zone] for zone in zones_up_to_failure],
    ]

    zone_dfs = {
        zone: spark.createDataFrame([(1,)], ['ID'])
        for zone in ZONES
        if zone != failing_zone
    }
    pipeline = _make_pipeline(
        zone_dfs=zone_dfs,
        run_tracker=run_tracker,
        raise_error_in=failing_zone,
    )

    with pytest.raises(ValueError, match='boom'):
        pipeline.run(workflow_run_id=uuid4())

    preceding_zones = zones_up_to_failure[:-1]
    for zone in preceding_zones:
        run_tracker.complete_execution.assert_any_call(zone_executions[zone].run_id)
    assert run_tracker.complete_execution.call_count == len(preceding_zones)

    run_tracker.fail_execution.assert_any_call(zone_executions[failing_zone].run_id)
    run_tracker.fail_execution.assert_any_call(pipeline_execution.run_id)
    assert run_tracker.fail_execution.call_count == 2
