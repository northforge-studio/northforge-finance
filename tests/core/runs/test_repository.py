from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from core.db import PostgresConfig, PostgresExecutor
from core.runs import (
    RunRepository,
    RunStatus,
    WorkflowRun,
    ExecutionRun,
    RunDependency,
)


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
        batch_id='1',
        status=RunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
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
    with pytest.raises(KeyError):
        repository.get_workflow_run(uuid4())


def test_update_workflow_status(repository, workflow_run):
    completed_at = datetime.now(timezone.utc)

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
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        retry_of_run_id=None,
    )

    repository.create_execution_run(run)
    fetched = repository.get_execution_run(run.run_id)

    assert fetched == run


def test_execution_run_links_to_parent_and_retry(repository, workflow_run):
    parent = ExecutionRun(
        run_id=uuid4(),
        workflow_run_id=workflow_run.workflow_run_id,
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.SUCCEEDED,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
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
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
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
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        retry_of_run_id=retried.run_id,
    )
    repository.create_execution_run(child)

    fetched = repository.get_execution_run(child.run_id)

    assert fetched.parent_run_id == parent.run_id
    assert fetched.retry_of_run_id == retried.run_id


def test_get_execution_run_unknown_id_raises(repository):
    with pytest.raises(KeyError):
        repository.get_execution_run(uuid4())


def _make_execution_run(workflow_run_id, **overrides):
    defaults = dict(
        run_id=uuid4(),
        workflow_run_id=workflow_run_id,
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.SUCCEEDED,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
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


def test_update_execution_status(repository, workflow_run):
    run = ExecutionRun(
        run_id=uuid4(),
        workflow_run_id=workflow_run.workflow_run_id,
        parent_run_id=None,
        component='foundry',
        operation='enrich',
        status=RunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        retry_of_run_id=None,
    )
    repository.create_execution_run(run)

    completed_at = datetime.now(timezone.utc)

    repository.update_execution_status(
        run.run_id,
        RunStatus.FAILED,
        completed_at=completed_at,
    )

    fetched = repository.get_execution_run(run.run_id)

    assert fetched.status == RunStatus.FAILED
    assert fetched.completed_at == completed_at
