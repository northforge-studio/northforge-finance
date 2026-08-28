from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.runs import RunRepository, RunStatus, RunTracker

from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA, POSTING_SCHEMA

from recon.manager import ReconManager
from recon.models import ReconRunResult


BUSINESS_DT = date(2026, 1, 1)


# -- fakes --------------------------------------------------------------

class _FakeRunRepository(RunRepository):
    """An in-memory stand-in for RunRepository, so RunTracker (the real,
    unmocked collaborator) can be exercised against ReconManager without a
    database. Mirrors tests/workflow/test_orchestrator.py's fake."""

    def __init__(self):
        self.workflows = {}
        self.executions = {}
        self.dependencies = []


    def create_workflow_run(self, run):
        self.workflows[run.workflow_run_id] = run


    def get_workflow_run(self, workflow_run_id):
        if workflow_run_id not in self.workflows:
            raise KeyError(f'Unknown workflow_run_id: {workflow_run_id!r}')
        return self.workflows[workflow_run_id]


    def create_execution_run(self, run):
        self.executions[run.run_id] = run


    def get_execution_run(self, run_id):
        return self.executions[run_id]


    def get_execution_runs(self, workflow_run_id):
        return tuple(
            execution
            for execution in self.executions.values()
            if execution.workflow_run_id == workflow_run_id
        )


    def update_workflow_status(self, workflow_run_id, status, completed_at=None):
        run = self.workflows[workflow_run_id]
        self.workflows[workflow_run_id] = replace(
            run, status=status, completed_at=completed_at,
        )


    def update_execution_status(self, run_id, status, completed_at=None):
        run = self.executions[run_id]
        self.executions[run_id] = replace(
            run, status=status, completed_at=completed_at,
        )


    def create_dependency(self, dependency):
        self.dependencies.append(dependency)


def _make_run_tracker():
    return RunTracker(_FakeRunRepository())


class _FakeGL:
    def __init__(self, postings_by_workflow=None):
        self._postings_by_workflow = postings_by_workflow or {}
        self.get_postings_calls = []


    def get_postings(self, workflow_run_id):
        self.get_postings_calls.append(workflow_run_id)
        return self._postings_by_workflow[workflow_run_id]


class _FakeReconRepository:
    def __init__(self, interface_by_workflow=None, raise_on_write=False):
        self._interface_by_workflow = interface_by_workflow or {}
        self._raise_on_write = raise_on_write
        self.written = []
        self.get_interface_calls = []


    def get_interface_trial_balance(self, workflow_run_id):
        self.get_interface_calls.append(workflow_run_id)
        return self._interface_by_workflow[workflow_run_id]


    def write_results(self, results):
        if self._raise_on_write:
            raise RuntimeError('write boom')
        self.written.extend(results)


# -- row builders ---------------------------------------------------------

def _interface_values(workflow_run_id, **overrides):
    values = dict(
        WORKFLOW_RUN_ID=str(workflow_run_id),
        PRODUCER_RUN_ID=str(uuid4()),
        DATACLASS='TRIAL_BALANCE',
        TRANSACTION_NUMBER='TXN-1',
        LINE_NUMBER='1',
        ENTITY_CD='USM',
        DEPT_CD='4000',
        BRANCH_CD='100',
        GL_ACCOUNT='123456',
        SUB_ACCOUNT='001',
        AFFILIATE_CD='AFF1',
        PRODUCT_CD='PRD1',
        BOOK_CD='BK1',
        SOURCE_CD='SRC1',
        CR_DR_IND='DR',
        FOUNDRY_RULE_ID='RULE-1',
        POSTING_ID='POST-1',
        POSTING_STREAM='STREAM-1',
        SRC_RECORD_ID='REC-1',
        SRC_APP_CD='NFM',
        TRANSACTION_CURRENCY='USD',
        TRANSACTION_AMOUNT=Decimal('100.00'),
        ACCOUNTED_CURRENCY='USD',
        ACCOUNTED_AMOUNT=Decimal('100.00'),
        FX_RATE=Decimal('1.0'),
        AS_OF_DATE=BUSINESS_DT,
        BUSINESS_DATE=BUSINESS_DT,
    )
    values.update(overrides)
    return tuple(values[name] for name in INTERFACE_TRIAL_BALANCE_SCHEMA.fieldNames())


def _posting_values(workflow_run_id, **overrides):
    values = dict(
        GL_POSTING_ID=str(uuid4()),
        POSTED_AT=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        WORKFLOW_RUN_ID=str(workflow_run_id),
        PRODUCER_RUN_ID=str(uuid4()),
        DATACLASS='TRIAL_BALANCE',
        TRANSACTION_NUMBER='TXN-1',
        LINE_NUMBER='1',
        FOUNDRY_RULE_ID='RULE-1',
        POSTING_ID='POST-1',
        POSTING_STREAM='STREAM-1',
        SRC_RECORD_ID='REC-1',
        SRC_APP_CD='NFM',
        ENTITY_CD='USM',
        DEPT_CD='4000',
        BRANCH_CD='100',
        GL_ACCOUNT='123456',
        SUB_ACCOUNT='001',
        AFFILIATE_CD='AFF1',
        PRODUCT_CD='PRD1',
        BOOK_CD='BK1',
        SOURCE_CD='SRC1',
        CR_DR_IND='DR',
        TRANSACTION_CURRENCY='USD',
        TRANSACTION_AMOUNT=Decimal('100.00'),
        ACCOUNTED_CURRENCY='USD',
        ACCOUNTED_AMOUNT=Decimal('100.00'),
        FX_RATE=Decimal('1.0'),
        AS_OF_DATE=BUSINESS_DT,
        BUSINESS_DATE=BUSINESS_DT,
    )
    values.update(overrides)
    return tuple(values[name] for name in POSTING_SCHEMA.fieldNames())


def _interface_df(spark, rows):
    return spark.createDataFrame(list(rows), schema=INTERFACE_TRIAL_BALANCE_SCHEMA)


def _posting_df(spark, rows):
    return spark.createDataFrame(list(rows), schema=POSTING_SCHEMA)


# -- fixtures ---------------------------------------------------------------

@pytest.fixture
def run_tracker():
    return _make_run_tracker()


@pytest.fixture
def workflow(run_tracker):
    return run_tracker.start_workflow(dataclass='TRIAL_BALANCE', business_dt=BUSINESS_DT)


def _manager(run_tracker, interface_df, gl_df, raise_on_write=False):
    workflow_run_id = list(run_tracker._repository.workflows)[0]

    repository = _FakeReconRepository(
        interface_by_workflow={workflow_run_id: interface_df},
        raise_on_write=raise_on_write,
    )
    gl = _FakeGL(postings_by_workflow={workflow_run_id: gl_df})

    return ReconManager(repository, run_tracker, gl), repository, gl


# -- successful execution -----------------------------------------------

def test_reconcile_returns_a_recon_run_result(spark, run_tracker, workflow):
    interface_df = _interface_df(spark, [_interface_values(workflow.workflow_run_id)])
    gl_df = _posting_df(spark, [_posting_values(workflow.workflow_run_id)])
    manager, _, _ = _manager(run_tracker, interface_df, gl_df)

    result = manager.reconcile(workflow.workflow_run_id)

    assert isinstance(result, ReconRunResult)
    assert result.workflow_run_id == workflow.workflow_run_id
    assert result.result_count == 1
    assert result.break_count == 0


def test_reconcile_persists_a_balanced_result_with_zero_difference(
    spark, run_tracker, workflow,
):
    interface_df = _interface_df(spark, [_interface_values(workflow.workflow_run_id)])
    gl_df = _posting_df(spark, [_posting_values(workflow.workflow_run_id)])
    manager, repository, _ = _manager(run_tracker, interface_df, gl_df)

    manager.reconcile(workflow.workflow_run_id)

    assert len(repository.written) == 1
    written = repository.written[0]
    assert written.interface_balance == Decimal('100.00')
    assert written.gl_balance == Decimal('100.00')
    assert written.difference_amount == Decimal('0.00')


def test_reconcile_flags_a_non_zero_difference_as_a_break(spark, run_tracker, workflow):
    interface_df = _interface_df(
        spark, [_interface_values(workflow.workflow_run_id, ACCOUNTED_AMOUNT=Decimal('100.00'))],
    )
    gl_df = _posting_df(
        spark, [_posting_values(workflow.workflow_run_id, ACCOUNTED_AMOUNT=Decimal('90.00'))],
    )
    manager, repository, _ = _manager(run_tracker, interface_df, gl_df)

    result = manager.reconcile(workflow.workflow_run_id)

    assert result.break_count == 1
    assert repository.written[0].difference_amount == Decimal('10.00')


def test_reconcile_stamps_workflow_run_id_and_the_recon_executions_run_id_as_producer(
    spark, run_tracker, workflow,
):
    interface_df = _interface_df(spark, [_interface_values(workflow.workflow_run_id)])
    gl_df = _posting_df(spark, [_posting_values(workflow.workflow_run_id)])
    manager, repository, _ = _manager(run_tracker, interface_df, gl_df)

    result = manager.reconcile(workflow.workflow_run_id)

    executions = run_tracker.get_execution_runs(workflow.workflow_run_id)
    [recon_execution] = [e for e in executions if e.component == 'recon']

    assert result.producer_run_id == recon_execution.run_id
    assert repository.written[0].workflow_run_id == workflow.workflow_run_id
    assert repository.written[0].producer_run_id == recon_execution.run_id


def test_reconcile_reads_interface_and_gl_scoped_to_the_workflow_run_id(
    spark, run_tracker, workflow,
):
    interface_df = _interface_df(spark, [_interface_values(workflow.workflow_run_id)])
    gl_df = _posting_df(spark, [_posting_values(workflow.workflow_run_id)])
    manager, repository, gl = _manager(run_tracker, interface_df, gl_df)

    manager.reconcile(workflow.workflow_run_id)

    assert repository.get_interface_calls == [workflow.workflow_run_id]
    assert gl.get_postings_calls == [workflow.workflow_run_id]


# -- execution lifecycle ---------------------------------------------------

def test_reconcile_creates_a_recon_execution_under_the_workflow(
    spark, run_tracker, workflow,
):
    interface_df = _interface_df(spark, [_interface_values(workflow.workflow_run_id)])
    gl_df = _posting_df(spark, [_posting_values(workflow.workflow_run_id)])
    manager, _, _ = _manager(run_tracker, interface_df, gl_df)

    manager.reconcile(workflow.workflow_run_id)

    executions = run_tracker.get_execution_runs(workflow.workflow_run_id)
    [recon_execution] = [e for e in executions if e.component == 'recon']

    assert recon_execution.operation == 'reconcile'
    assert recon_execution.workflow_run_id == workflow.workflow_run_id


def test_reconcile_completes_the_execution_on_success(spark, run_tracker, workflow):
    interface_df = _interface_df(spark, [_interface_values(workflow.workflow_run_id)])
    gl_df = _posting_df(spark, [_posting_values(workflow.workflow_run_id)])
    manager, _, _ = _manager(run_tracker, interface_df, gl_df)

    manager.reconcile(workflow.workflow_run_id)

    executions = run_tracker.get_execution_runs(workflow.workflow_run_id)
    [recon_execution] = [e for e in executions if e.component == 'recon']

    assert recon_execution.status == RunStatus.SUCCEEDED
    assert recon_execution.completed_at is not None


def test_reconcile_fails_the_execution_and_reraises_on_a_technical_failure(
    spark, run_tracker, workflow,
):
    interface_df = _interface_df(spark, [_interface_values(workflow.workflow_run_id)])
    gl_df = _posting_df(spark, [_posting_values(workflow.workflow_run_id)])
    manager, _, _ = _manager(run_tracker, interface_df, gl_df, raise_on_write=True)

    with pytest.raises(RuntimeError, match='write boom'):
        manager.reconcile(workflow.workflow_run_id)

    executions = run_tracker.get_execution_runs(workflow.workflow_run_id)
    [recon_execution] = [e for e in executions if e.component == 'recon']

    assert recon_execution.status == RunStatus.FAILED
    assert recon_execution.completed_at is not None


# -- dataclass/workflow validation ------------------------------------------

def test_reconcile_raises_for_unknown_workflow_run_id(run_tracker):
    manager = ReconManager(_FakeReconRepository(), run_tracker, _FakeGL())

    with pytest.raises(KeyError):
        manager.reconcile(uuid4())


def test_reconcile_raises_for_an_unsupported_dataclass_and_starts_no_execution(
    run_tracker,
):
    workflow = run_tracker.start_workflow(dataclass='POSITION', business_dt=BUSINESS_DT)
    manager = ReconManager(_FakeReconRepository(), run_tracker, _FakeGL())

    with pytest.raises(ValueError, match='POSITION'):
        manager.reconcile(workflow.workflow_run_id)

    assert run_tracker.get_execution_runs(workflow.workflow_run_id) == ()
