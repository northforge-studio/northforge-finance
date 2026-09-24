from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from core.db import PostgresConfig, PostgresExecutor
from core.runs import RunRepository
from core.runs.models import (
    RunStatus,
    WorkflowRun,
    ExecutionRun,
    RunDependency,
    WorkflowRunSummary,
)

from tests.support.constants import TIMESTAMP


@pytest.fixture(scope='module')
def executor():
    return PostgresExecutor(PostgresConfig.from_env())


@pytest.fixture(scope='module')
def repository():
    return RunRepository()


@pytest.fixture
def workflow_run(repository, executor):
    run = WorkflowRun(
        workflow_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        status=RunStatus.RUNNING,
        started_at=TIMESTAMP,
        completed_at=None,
    )
    repository.create_workflow_run(run)

    yield run

    executor.execute(
        'DELETE FROM core.run_dependency '
        'WHERE consumer_run_id IN ('
        '    SELECT run_id FROM core.execution_run '
        '    WHERE workflow_run_id = :workflow_run_id'
        ')',
        {'workflow_run_id': run.workflow_run_id},
    )
    executor.execute(
        'DELETE FROM core.execution_run '
        'WHERE workflow_run_id = :workflow_run_id',
        {'workflow_run_id': run.workflow_run_id},
    )
    executor.execute(
        'DELETE FROM core.workflow_run '
        'WHERE workflow_run_id = :workflow_run_id',
        {'workflow_run_id': run.workflow_run_id},
    )


def test_create_and_get_workflow_run(repository, workflow_run):
    fetched = repository.get_workflow_run(workflow_run.workflow_run_id)

    assert fetched == workflow_run


def test_get_workflow_run_unknown_id_raises(repository):
    with pytest.raises(KeyError, match='Unknown workflow_run_id'):
        repository.get_workflow_run(uuid4())


def test_update_workflow_status(repository, workflow_run):
    completed_at = TIMESTAMP

    repository.update_workflow_status(
        workflow_run.workflow_run_id,
        RunStatus.SUCCEEDED,
        completed_at=completed_at,
    )

    fetched = repository.get_workflow_run(workflow_run.workflow_run_id)

    assert fetched.status == RunStatus.SUCCEEDED
    assert fetched.completed_at == completed_at


def test_create_and_get_execution_run(repository, workflow_run):
    run = ExecutionRun(
        run_id=uuid4(),
        workflow_run_id=workflow_run.workflow_run_id,
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.RUNNING,
        started_at=TIMESTAMP,
        completed_at=None,
        retry_of_run_id=None,
    )

    repository.create_execution_run(run)
    fetched = repository.get_execution_run(run.run_id)

    assert fetched == run


def test_create_and_get_execution_run_links_to_parent_and_retry(repository, workflow_run):
    parent = ExecutionRun(
        run_id=uuid4(),
        workflow_run_id=workflow_run.workflow_run_id,
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.SUCCEEDED,
        started_at=TIMESTAMP,
        completed_at=TIMESTAMP,
        retry_of_run_id=None,
    )
    repository.create_execution_run(parent)

    retried = ExecutionRun(
        run_id=uuid4(),
        workflow_run_id=workflow_run.workflow_run_id,
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.FAILED,
        started_at=TIMESTAMP,
        completed_at=TIMESTAMP,
        retry_of_run_id=None,
    )
    repository.create_execution_run(retried)

    child = ExecutionRun(
        run_id=uuid4(),
        workflow_run_id=workflow_run.workflow_run_id,
        parent_run_id=parent.run_id,
        component='foundry',
        operation='enrich',
        status=RunStatus.RUNNING,
        started_at=TIMESTAMP,
        completed_at=None,
        retry_of_run_id=retried.run_id,
    )
    repository.create_execution_run(child)

    fetched = repository.get_execution_run(child.run_id)

    assert fetched.parent_run_id == parent.run_id
    assert fetched.retry_of_run_id == retried.run_id


def test_get_execution_run_unknown_id_raises(repository):
    with pytest.raises(KeyError, match='Unknown run_id'):
        repository.get_execution_run(uuid4())


def _make_execution_run(workflow_run_id, **overrides) -> ExecutionRun:
    defaults = dict(
        run_id=uuid4(),
        workflow_run_id=workflow_run_id,
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.SUCCEEDED,
        started_at=TIMESTAMP,
        completed_at=TIMESTAMP,
        retry_of_run_id=None,
    )
    defaults.update(overrides)
    return ExecutionRun(**defaults)


def test_create_and_get_dependency(repository, workflow_run):
    consumer = _make_execution_run(workflow_run.workflow_run_id)
    producer = _make_execution_run(workflow_run.workflow_run_id)
    repository.create_execution_run(consumer)
    repository.create_execution_run(producer)

    dependency = RunDependency(
        consumer_run_id=consumer.run_id,
        producer_run_id=producer.run_id,
        input_role='posting',
    )
    repository.create_dependency(dependency)

    fetched = repository.get_dependencies(consumer.run_id)

    assert fetched == (dependency,)


def test_get_dependencies_supports_multiple_producers(repository, workflow_run):
    consumer = _make_execution_run(
        workflow_run.workflow_run_id,
        component='recon',
        operation='reconcile',
    )
    posting_producer = _make_execution_run(
        workflow_run.workflow_run_id,
        component='foundry',
        operation='posting',
    )
    oracle_producer = _make_execution_run(
        workflow_run.workflow_run_id,
        component='oracle',
        operation='accounting',
    )
    repository.create_execution_run(consumer)
    repository.create_execution_run(posting_producer)
    repository.create_execution_run(oracle_producer)

    posting_dependency = RunDependency(
        consumer_run_id=consumer.run_id,
        producer_run_id=posting_producer.run_id,
        input_role='posting',
    )
    oracle_dependency = RunDependency(
        consumer_run_id=consumer.run_id,
        producer_run_id=oracle_producer.run_id,
        input_role='oracle_accounting',
    )
    repository.create_dependency(posting_dependency)
    repository.create_dependency(oracle_dependency)

    fetched = repository.get_dependencies(consumer.run_id)

    assert set(fetched) == {posting_dependency, oracle_dependency}


def test_get_dependencies_defaults_input_role_to_none(repository, workflow_run):
    consumer = _make_execution_run(workflow_run.workflow_run_id)
    producer = _make_execution_run(workflow_run.workflow_run_id)
    repository.create_execution_run(consumer)
    repository.create_execution_run(producer)

    dependency = RunDependency(
        consumer_run_id=consumer.run_id,
        producer_run_id=producer.run_id,
    )
    repository.create_dependency(dependency)

    fetched = repository.get_dependencies(consumer.run_id)

    assert fetched == (dependency,)
    assert fetched[0].input_role is None


def test_get_dependencies_returns_empty_tuple_when_none_exist(repository, workflow_run):
    consumer = _make_execution_run(workflow_run.workflow_run_id)
    repository.create_execution_run(consumer)

    assert repository.get_dependencies(consumer.run_id) == ()


def test_get_execution_runs_returns_all_executions_for_workflow(repository, workflow_run):
    first = _make_execution_run(
        workflow_run.workflow_run_id,
        started_at=datetime(2026, 8, 24, 10, 0, tzinfo=timezone.utc),
    )
    second = _make_execution_run(
        workflow_run.workflow_run_id,
        started_at=datetime(2026, 8, 24, 10, 1, tzinfo=timezone.utc),
    )
    repository.create_execution_run(first)
    repository.create_execution_run(second)

    fetched = repository.get_execution_runs(workflow_run.workflow_run_id)

    assert fetched == (first, second)


def test_get_execution_runs_excludes_other_workflows(repository, workflow_run, executor):
    other_workflow = WorkflowRun(
        workflow_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        status=RunStatus.RUNNING,
        started_at=TIMESTAMP,
        completed_at=None,
    )
    repository.create_workflow_run(other_workflow)

    own_run = _make_execution_run(workflow_run.workflow_run_id)
    other_run = _make_execution_run(other_workflow.workflow_run_id)
    repository.create_execution_run(own_run)
    repository.create_execution_run(other_run)

    try:
        fetched = repository.get_execution_runs(workflow_run.workflow_run_id)

        assert fetched == (own_run,)
    finally:
        executor.execute(
            'DELETE FROM core.execution_run WHERE workflow_run_id = :workflow_run_id',
            {'workflow_run_id': other_workflow.workflow_run_id},
        )
        executor.execute(
            'DELETE FROM core.workflow_run WHERE workflow_run_id = :workflow_run_id',
            {'workflow_run_id': other_workflow.workflow_run_id},
        )


def test_get_execution_runs_returns_empty_tuple_when_none_exist(repository, workflow_run):
    assert repository.get_execution_runs(workflow_run.workflow_run_id) == ()


def test_update_execution_status(repository, workflow_run):
    run = ExecutionRun(
        run_id=uuid4(),
        workflow_run_id=workflow_run.workflow_run_id,
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.RUNNING,
        started_at=TIMESTAMP,
        completed_at=None,
        retry_of_run_id=None,
    )
    repository.create_execution_run(run)

    completed_at = TIMESTAMP

    repository.update_execution_status(
        run.run_id,
        RunStatus.FAILED,
        completed_at=completed_at,
    )

    fetched = repository.get_execution_run(run.run_id)

    assert fetched.status == RunStatus.FAILED
    assert fetched.completed_at == completed_at


def test_get_workflow_dependencies_returns_dependencies_for_workflow(
    repository, workflow_run,
):
    producer = _make_execution_run(workflow_run.workflow_run_id)
    consumer = _make_execution_run(workflow_run.workflow_run_id)
    repository.create_execution_run(producer)
    repository.create_execution_run(consumer)

    dependency = RunDependency(
        consumer_run_id=consumer.run_id,
        producer_run_id=producer.run_id,
        input_role='staging',
    )
    repository.create_dependency(dependency)

    fetched = repository.get_workflow_dependencies(workflow_run.workflow_run_id)

    assert fetched == (dependency,)


def test_get_workflow_dependencies_excludes_other_workflows(
    repository, workflow_run, executor,
):
    other_workflow = WorkflowRun(
        workflow_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        status=RunStatus.RUNNING,
        started_at=TIMESTAMP,
        completed_at=None,
    )
    repository.create_workflow_run(other_workflow)

    own_producer = _make_execution_run(workflow_run.workflow_run_id)
    own_consumer = _make_execution_run(workflow_run.workflow_run_id)
    repository.create_execution_run(own_producer)
    repository.create_execution_run(own_consumer)
    own_dependency = RunDependency(
        consumer_run_id=own_consumer.run_id,
        producer_run_id=own_producer.run_id,
        input_role='staging',
    )
    repository.create_dependency(own_dependency)

    other_producer = _make_execution_run(other_workflow.workflow_run_id)
    other_consumer = _make_execution_run(other_workflow.workflow_run_id)
    repository.create_execution_run(other_producer)
    repository.create_execution_run(other_consumer)
    other_dependency = RunDependency(
        consumer_run_id=other_consumer.run_id,
        producer_run_id=other_producer.run_id,
        input_role='staging',
    )
    repository.create_dependency(other_dependency)

    try:
        fetched = repository.get_workflow_dependencies(workflow_run.workflow_run_id)

        assert fetched == (own_dependency,)
    finally:
        executor.execute(
            'DELETE FROM core.run_dependency WHERE consumer_run_id IN ('
            '    SELECT run_id FROM core.execution_run '
            '    WHERE workflow_run_id = :workflow_run_id'
            ')',
            {'workflow_run_id': other_workflow.workflow_run_id},
        )
        executor.execute(
            'DELETE FROM core.execution_run WHERE workflow_run_id = :workflow_run_id',
            {'workflow_run_id': other_workflow.workflow_run_id},
        )
        executor.execute(
            'DELETE FROM core.workflow_run WHERE workflow_run_id = :workflow_run_id',
            {'workflow_run_id': other_workflow.workflow_run_id},
        )


def test_get_workflow_dependencies_returns_empty_tuple_when_none_exist(
    repository, workflow_run,
):
    run = _make_execution_run(workflow_run.workflow_run_id)
    repository.create_execution_run(run)

    assert repository.get_workflow_dependencies(workflow_run.workflow_run_id) == ()


def test_get_workflow_summary_returns_workflow_executions_and_dependencies(
    repository, workflow_run,
):
    producer = _make_execution_run(workflow_run.workflow_run_id)
    consumer = _make_execution_run(workflow_run.workflow_run_id)
    repository.create_execution_run(producer)
    repository.create_execution_run(consumer)

    dependency = RunDependency(
        consumer_run_id=consumer.run_id,
        producer_run_id=producer.run_id,
        input_role='staging',
    )
    repository.create_dependency(dependency)

    summary = repository.get_workflow_summary(workflow_run.workflow_run_id)

    assert isinstance(summary, WorkflowRunSummary)
    assert summary.workflow == workflow_run
    assert set(summary.executions) == {producer, consumer}
    assert summary.dependencies == (dependency,)


def test_get_workflow_summary_with_no_executions(repository, workflow_run):
    summary = repository.get_workflow_summary(workflow_run.workflow_run_id)

    assert summary.workflow == workflow_run
    assert summary.executions == ()
    assert summary.dependencies == ()


def test_get_workflow_summary_unknown_workflow_raises(repository):
    with pytest.raises(KeyError, match='Unknown workflow_run_id'):
        repository.get_workflow_summary(uuid4())
