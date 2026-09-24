from decimal import Decimal
from uuid import uuid4

import pytest

from core.runs.models import RunStatus

from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA, POSTING_SCHEMA

from recon.manager import ReconManager
from recon.models import ReconRunResult

from tests.recon.factories import make_interface_values, make_posting_values
from tests.recon.fakes import FakeGL
from tests.support.constants import BUSINESS_DT


# -- fakes --------------------------------------------------------------

class _FakeReconRepository:
    def __init__(self, interface_by_workflow=None, raise_on_write=False, results_by_workflow=None):
        self._interface_by_workflow = interface_by_workflow or {}
        self._raise_on_write = raise_on_write
        self._results_by_workflow = results_by_workflow or {}
        self.written = []
        self.get_interface_calls = []
        self.get_results_calls = []


    def get_interface_trial_balance(self, workflow_run_id):
        self.get_interface_calls.append(workflow_run_id)
        return self._interface_by_workflow[workflow_run_id]


    def write_results(self, results):
        if self._raise_on_write:
            raise RuntimeError('write boom')
        self.written.extend(results)


    def get_results(self, workflow_run_id):
        self.get_results_calls.append(workflow_run_id)
        return self._results_by_workflow[workflow_run_id]


# -- row builders ---------------------------------------------------------

def _make_interface_df(spark, rows):
    return spark.createDataFrame(list(rows), schema=INTERFACE_TRIAL_BALANCE_SCHEMA)


def _make_posting_df(spark, rows):
    return spark.createDataFrame(list(rows), schema=POSTING_SCHEMA)


# -- helpers ---------------------------------------------------------------

def _make_manager(run_tracker, interface_df, gl_df, raise_on_write=False):
    workflow_run_id = list(run_tracker._repository.workflows)[0]

    repository = _FakeReconRepository(
        interface_by_workflow={workflow_run_id: interface_df},
        raise_on_write=raise_on_write,
    )
    gl = FakeGL(postings_by_workflow={workflow_run_id: gl_df})

    return ReconManager(repository, run_tracker, gl), repository, gl


# -- successful execution -----------------------------------------------

def test_reconcile_returns_a_recon_run_result(spark, run_tracker, workflow):
    interface_df = _make_interface_df(spark, [make_interface_values(workflow.workflow_run_id)])
    gl_df = _make_posting_df(spark, [make_posting_values(workflow.workflow_run_id)])
    manager, _, _ = _make_manager(run_tracker, interface_df, gl_df)

    result = manager.reconcile(workflow.workflow_run_id)

    assert isinstance(result, ReconRunResult)
    assert result.workflow_run_id == workflow.workflow_run_id
    assert result.result_count == 1
    assert result.break_count == 0


def test_reconcile_persists_a_balanced_result_with_zero_difference(
    spark, run_tracker, workflow,
):
    interface_df = _make_interface_df(spark, [make_interface_values(workflow.workflow_run_id)])
    gl_df = _make_posting_df(spark, [make_posting_values(workflow.workflow_run_id)])
    manager, repository, _ = _make_manager(run_tracker, interface_df, gl_df)

    manager.reconcile(workflow.workflow_run_id)

    assert len(repository.written) == 1
    written = repository.written[0]
    assert written.interface_balance == Decimal('100.00')
    assert written.gl_balance == Decimal('100.00')
    assert written.difference_amount == Decimal('0.00')


def test_reconcile_flags_a_non_zero_difference_as_a_break(spark, run_tracker, workflow):
    interface_df = _make_interface_df(
        spark, [make_interface_values(workflow.workflow_run_id, ACCOUNTED_AMOUNT=Decimal('100.00'))],
    )
    gl_df = _make_posting_df(
        spark, [make_posting_values(workflow.workflow_run_id, ACCOUNTED_AMOUNT=Decimal('90.00'))],
    )
    manager, repository, _ = _make_manager(run_tracker, interface_df, gl_df)

    result = manager.reconcile(workflow.workflow_run_id)

    assert result.break_count == 1
    assert repository.written[0].difference_amount == Decimal('10.00')


def test_reconcile_stamps_workflow_run_id_and_execution_run_id_as_producer(
    spark, run_tracker, workflow,
):
    interface_df = _make_interface_df(spark, [make_interface_values(workflow.workflow_run_id)])
    gl_df = _make_posting_df(spark, [make_posting_values(workflow.workflow_run_id)])
    manager, repository, _ = _make_manager(run_tracker, interface_df, gl_df)

    result = manager.reconcile(workflow.workflow_run_id)

    executions = run_tracker.get_execution_runs(workflow.workflow_run_id)
    [recon_execution] = [e for e in executions if e.component == 'recon']

    assert result.producer_run_id == recon_execution.run_id
    assert repository.written[0].workflow_run_id == workflow.workflow_run_id
    assert repository.written[0].producer_run_id == recon_execution.run_id


def test_reconcile_reads_interface_and_gl_scoped_to_the_workflow_run_id(
    spark, run_tracker, workflow,
):
    interface_df = _make_interface_df(spark, [make_interface_values(workflow.workflow_run_id)])
    gl_df = _make_posting_df(spark, [make_posting_values(workflow.workflow_run_id)])
    manager, repository, gl = _make_manager(run_tracker, interface_df, gl_df)

    manager.reconcile(workflow.workflow_run_id)

    assert repository.get_interface_calls == [workflow.workflow_run_id]
    assert gl.get_postings_calls == [workflow.workflow_run_id]


def test_get_results_delegates_to_the_repository(spark, run_tracker, workflow):
    sentinel_df = spark.createDataFrame([(1,)], ['X'])
    repository = _FakeReconRepository(
        results_by_workflow={workflow.workflow_run_id: sentinel_df},
    )
    manager = ReconManager(repository, run_tracker, FakeGL())

    result = manager.get_results(workflow.workflow_run_id)

    assert result is sentinel_df
    assert repository.get_results_calls == [workflow.workflow_run_id]


# -- execution lifecycle ---------------------------------------------------

def test_reconcile_creates_a_recon_execution_under_the_workflow(
    spark, run_tracker, workflow,
):
    interface_df = _make_interface_df(spark, [make_interface_values(workflow.workflow_run_id)])
    gl_df = _make_posting_df(spark, [make_posting_values(workflow.workflow_run_id)])
    manager, _, _ = _make_manager(run_tracker, interface_df, gl_df)

    manager.reconcile(workflow.workflow_run_id)

    executions = run_tracker.get_execution_runs(workflow.workflow_run_id)
    [recon_execution] = [e for e in executions if e.component == 'recon']

    assert recon_execution.operation == 'reconcile'
    assert recon_execution.workflow_run_id == workflow.workflow_run_id


def test_reconcile_completes_the_execution_on_success(spark, run_tracker, workflow):
    interface_df = _make_interface_df(spark, [make_interface_values(workflow.workflow_run_id)])
    gl_df = _make_posting_df(spark, [make_posting_values(workflow.workflow_run_id)])
    manager, _, _ = _make_manager(run_tracker, interface_df, gl_df)

    manager.reconcile(workflow.workflow_run_id)

    executions = run_tracker.get_execution_runs(workflow.workflow_run_id)
    [recon_execution] = [e for e in executions if e.component == 'recon']

    assert recon_execution.status == RunStatus.SUCCEEDED
    assert recon_execution.completed_at is not None


def test_reconcile_fails_the_execution_and_reraises_on_a_technical_failure(
    spark, run_tracker, workflow,
):
    interface_df = _make_interface_df(spark, [make_interface_values(workflow.workflow_run_id)])
    gl_df = _make_posting_df(spark, [make_posting_values(workflow.workflow_run_id)])
    manager, _, _ = _make_manager(run_tracker, interface_df, gl_df, raise_on_write=True)

    with pytest.raises(RuntimeError, match='write boom'):
        manager.reconcile(workflow.workflow_run_id)

    executions = run_tracker.get_execution_runs(workflow.workflow_run_id)
    [recon_execution] = [e for e in executions if e.component == 'recon']

    assert recon_execution.status == RunStatus.FAILED
    assert recon_execution.completed_at is not None


# -- dataclass/workflow validation ------------------------------------------

def test_reconcile_raises_for_unknown_workflow_run_id(run_tracker):
    manager = ReconManager(_FakeReconRepository(), run_tracker, FakeGL())

    with pytest.raises(KeyError):
        manager.reconcile(uuid4())


def test_reconcile_raises_for_an_unsupported_dataclass_and_starts_no_execution(
    run_tracker,
):
    workflow = run_tracker.start_workflow(dataclass='POSITION', business_dt=BUSINESS_DT)
    manager = ReconManager(_FakeReconRepository(), run_tracker, FakeGL())

    with pytest.raises(ValueError, match='POSITION'):
        manager.reconcile(workflow.workflow_run_id)

    assert run_tracker.get_execution_runs(workflow.workflow_run_id) == ()
