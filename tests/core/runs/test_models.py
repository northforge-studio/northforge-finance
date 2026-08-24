from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from core.runs import RunStatus, WorkflowRun, ExecutionRun


def _make_workflow_run(**overrides):
    defaults = dict(
        workflow_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        batch_id='1',
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


def test_run_status_values():
    assert set(RunStatus) == {
        RunStatus.PENDING,
        RunStatus.RUNNING,
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    }
