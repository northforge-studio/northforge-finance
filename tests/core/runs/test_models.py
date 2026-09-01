from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from core.runs.models import (
    RunStatus,
    WorkflowRun,
    ExecutionRun,
    RunDependency,
    RunIdentity,
    ZoneResult,
    PipelineResult,
)


def _make_workflow_run(**overrides):
    defaults = dict(
        workflow_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        status=RunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
    )
    defaults.update(overrides)
    return WorkflowRun(**defaults)


def _make_execution_run(**overrides):
    defaults = dict(
        run_id=uuid4(),
        workflow_run_id=uuid4(),
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        retry_of_run_id=None,
    )
    defaults.update(overrides)
    return ExecutionRun(**defaults)


def test_workflow_run_is_frozen():
    run = _make_workflow_run()

    with pytest.raises(FrozenInstanceError):
        run.status = RunStatus.SUCCEEDED


def test_execution_run_is_frozen():
    run = _make_execution_run()

    with pytest.raises(FrozenInstanceError):
        run.status = RunStatus.SUCCEEDED


def test_execution_run_links_to_parent_and_retry():
    parent = _make_execution_run()
    retried = _make_execution_run()

    child = _make_execution_run(
        parent_run_id=parent.run_id,
        retry_of_run_id=retried.run_id,
    )

    assert child.parent_run_id == parent.run_id
    assert child.retry_of_run_id == retried.run_id


def test_run_dependency_is_frozen():
    dependency = RunDependency(
        consumer_run_id=uuid4(),
        producer_run_id=uuid4(),
        input_role='posting',
    )

    with pytest.raises(FrozenInstanceError):
        dependency.input_role = 'oracle_accounting'


def test_run_dependency_input_role_defaults_to_none():
    dependency = RunDependency(
        consumer_run_id=uuid4(),
        producer_run_id=uuid4(),
    )

    assert dependency.input_role is None


def test_run_status_values():
    assert set(RunStatus) == {
        RunStatus.PENDING,
        RunStatus.RUNNING,
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }


def _make_identity(**overrides):
    defaults = dict(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=None,
    )
    defaults.update(overrides)
    return RunIdentity(**defaults)


def _make_zone_result(**overrides):
    defaults = dict(
        identity=_make_identity(),
        zone='STAGING',
        status=RunStatus.SUCCEEDED,
        record_count=100,
    )
    defaults.update(overrides)
    return ZoneResult(**defaults)


def test_run_identity_is_frozen():
    identity = _make_identity()

    with pytest.raises(FrozenInstanceError):
        identity.run_id = uuid4()


def test_zone_result_is_frozen():
    zone_result = _make_zone_result()

    with pytest.raises(FrozenInstanceError):
        zone_result.status = RunStatus.FAILED


def test_zone_result_carries_its_identity():
    identity = _make_identity()
    zone_result = _make_zone_result(identity=identity)

    assert zone_result.identity is identity
    assert zone_result.identity.run_id == identity.run_id


def test_pipeline_result_is_frozen():
    identity = _make_identity()
    pipeline_result = PipelineResult(
        identity=identity,
        status=RunStatus.SUCCEEDED,
        zones=(),
    )

    with pytest.raises(FrozenInstanceError):
        pipeline_result.status = RunStatus.FAILED


def test_pipeline_result_aggregates_zone_results():
    identity = _make_identity()

    staging = _make_zone_result(identity=identity, zone='STAGING')
    enrichment = _make_zone_result(identity=identity, zone='ENRICHMENT')

    pipeline_result = PipelineResult(
        identity=identity,
        status=RunStatus.SUCCEEDED,
        zones=(staging, enrichment),
    )

    assert pipeline_result.identity == identity
    assert [zone.zone for zone in pipeline_result.zones] == [
        'STAGING',
        'ENRICHMENT',
    ]
    assert all(
        zone.identity == identity
        for zone in pipeline_result.zones
    )


def test_pipeline_result_accepts_no_zones():
    identity = _make_identity()

    pipeline_result = PipelineResult(
        identity=identity,
        status=RunStatus.PENDING,
        zones=(),
    )

    assert pipeline_result.zones == ()
