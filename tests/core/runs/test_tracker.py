from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from core.runs import RunRepository, RunTracker
from core.runs.models import (
    RunStatus,
    WorkflowRun,
    ExecutionRun,
    RunDependency,
)

from tests.support.constants import BUSINESS_DT


def _tracker():
    repository = MagicMock(spec=RunRepository)
    return RunTracker(repository), repository


def test_start_workflow_persists_running_run_and_returns_it():
    tracker, repository = _tracker()

    run = tracker.start_workflow(
        dataclass='TRIAL_BALANCE',
        business_dt=BUSINESS_DT,
    )

    assert isinstance(run, WorkflowRun)
    assert isinstance(run.workflow_run_id, UUID)
    assert run.dataclass == 'TRIAL_BALANCE'
    assert run.business_dt == BUSINESS_DT
    assert run.status == RunStatus.RUNNING
    assert run.started_at.tzinfo is not None
    assert run.completed_at is None

    repository.create_workflow_run.assert_called_once_with(run)


def test_start_workflow_generates_unique_ids():
    tracker, _ = _tracker()

    first = tracker.start_workflow(
        dataclass='TRIAL_BALANCE',
        business_dt=BUSINESS_DT,
    )
    second = tracker.start_workflow(
        dataclass='TRIAL_BALANCE',
        business_dt=BUSINESS_DT,
    )

    assert first.workflow_run_id != second.workflow_run_id


def test_start_execution_persists_running_run_and_returns_it():
    tracker, repository = _tracker()
    workflow_run_id = uuid4()

    run = tracker.start_execution(
        workflow_run_id=workflow_run_id,
        component='foundry',
        operation='enrich',
    )

    assert isinstance(run, ExecutionRun)
    assert isinstance(run.run_id, UUID)
    assert run.workflow_run_id == workflow_run_id
    assert run.component == 'foundry'
    assert run.operation == 'enrich'
    assert run.parent_run_id is None
    assert run.retry_of_run_id is None
    assert run.status == RunStatus.RUNNING
    assert run.started_at.tzinfo is not None
    assert run.completed_at is None

    repository.create_execution_run.assert_called_once_with(run)


def test_start_execution_links_parent_and_retry():
    tracker, _ = _tracker()
    workflow_run_id = uuid4()
    parent_run_id = uuid4()
    retry_of_run_id = uuid4()

    run = tracker.start_execution(
        workflow_run_id=workflow_run_id,
        component='foundry',
        operation='enrich',
        parent_run_id=parent_run_id,
        retry_of_run_id=retry_of_run_id,
    )

    assert run.parent_run_id == parent_run_id
    assert run.retry_of_run_id == retry_of_run_id


def test_complete_workflow_sets_succeeded_with_completed_at():
    tracker, repository = _tracker()
    workflow_run_id = uuid4()

    tracker.complete_workflow(workflow_run_id)

    repository.update_workflow_status.assert_called_once()
    args, kwargs = repository.update_workflow_status.call_args
    assert args[0] == workflow_run_id
    assert args[1] == RunStatus.SUCCEEDED
    assert isinstance(kwargs['completed_at'], datetime)
    assert kwargs['completed_at'].tzinfo is not None


def test_fail_workflow_sets_failed_with_completed_at():
    tracker, repository = _tracker()
    workflow_run_id = uuid4()

    tracker.fail_workflow(workflow_run_id)

    repository.update_workflow_status.assert_called_once()
    args, kwargs = repository.update_workflow_status.call_args
    assert args[0] == workflow_run_id
    assert args[1] == RunStatus.FAILED
    assert isinstance(kwargs['completed_at'], datetime)
    assert kwargs['completed_at'].tzinfo is not None


def test_complete_execution_sets_succeeded_with_completed_at():
    tracker, repository = _tracker()
    run_id = uuid4()

    tracker.complete_execution(run_id)

    repository.update_execution_status.assert_called_once()
    args, kwargs = repository.update_execution_status.call_args
    assert args[0] == run_id
    assert args[1] == RunStatus.SUCCEEDED
    assert isinstance(kwargs['completed_at'], datetime)
    assert kwargs['completed_at'].tzinfo is not None


def test_fail_execution_sets_failed_with_completed_at():
    tracker, repository = _tracker()
    run_id = uuid4()

    tracker.fail_execution(run_id)

    repository.update_execution_status.assert_called_once()
    args, kwargs = repository.update_execution_status.call_args
    assert args[0] == run_id
    assert args[1] == RunStatus.FAILED
    assert isinstance(kwargs['completed_at'], datetime)
    assert kwargs['completed_at'].tzinfo is not None


def test_add_dependency_persists_run_dependency():
    tracker, repository = _tracker()
    consumer_run_id = uuid4()
    producer_run_id = uuid4()

    tracker.add_dependency(
        consumer_run_id=consumer_run_id,
        producer_run_id=producer_run_id,
        input_role='STAGING',
    )

    repository.create_dependency.assert_called_once_with(
        RunDependency(
            consumer_run_id=consumer_run_id,
            producer_run_id=producer_run_id,
            input_role='STAGING',
        )
    )


def test_add_dependency_input_role_defaults_to_none():
    tracker, repository = _tracker()
    consumer_run_id = uuid4()
    producer_run_id = uuid4()

    tracker.add_dependency(
        consumer_run_id=consumer_run_id,
        producer_run_id=producer_run_id,
    )

    repository.create_dependency.assert_called_once_with(
        RunDependency(
            consumer_run_id=consumer_run_id,
            producer_run_id=producer_run_id,
            input_role=None,
        )
    )
