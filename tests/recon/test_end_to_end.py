# End-to-end coverage for the recon boundary: Interface -> GL -> Recon.
#
# Foundry's zone execution itself is intentionally not driven here: the
# committed demo wiring in scripts/test_foundry.py already fails against
# this environment for reasons unrelated to recon (it points AtlasClient
# at CSV files that no longer exist; Atlas data now lives in the atlas.*
# Postgres tables). Recon's own contract starts at Interface, so this
# test seeds interface.trial_balance directly with the same rows Foundry
# would have produced, then drives the real GLClient and ReconClient
# public APIs -- nothing about GL or recon itself is faked.
from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from core.store import CsvStore
from core.runs import RunRepository, RunTracker

from gl import GLClient
from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA
from gl.models import GLInstruction
from registry import SegmentType

from recon import ReconClient, ReconRunResult
from recon.repository import ReconRepository


BUSINESS_DT = date(2026, 3, 31)


class _FakeRunRepository(RunRepository):
    """In-memory RunRepository stand-in (mirrors
    tests/workflow/test_orchestrator.py), so the real RunTracker can run
    without touching the shared dev database."""

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


class _FakeRegistryClient:
    """Duck-types RegistryClient.validate_segment, as in tests/gl/test_client.py."""

    def __init__(self, valid_segments):
        self._valid_segments = valid_segments


    def validate_segment(self, segment, business_dt, segment_cd):
        return (segment, business_dt, segment_cd) in self._valid_segments


VALID_SEGMENTS = {
    (SegmentType.ENTITY, BUSINESS_DT, 'USM'),
    (SegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
    (SegmentType.BRANCH, BUSINESS_DT, '100'),
    (SegmentType.ACCOUNT, BUSINESS_DT, '123456'),
    (SegmentType.ACCOUNT, BUSINESS_DT, '223456'),
    (SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
    (SegmentType.AFFILIATE, BUSINESS_DT, '999999'),
    (SegmentType.PRODUCT, BUSINESS_DT, 'PRD1'),
    (SegmentType.BOOK, BUSINESS_DT, 'BK1'),
    (SegmentType.SOURCE, BUSINESS_DT, 'SRC1'),
}


def _instruction(workflow_run_id: UUID, **overrides) -> GLInstruction:
    fields = dict(
        workflow_run_id=workflow_run_id,
        producer_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        transaction_number='TXN-1',
        line_number='1',
        foundry_rule_id='RULE-1',
        posting_id='POST-1',
        posting_stream='GROSS_UP',
        src_record_id='REC-1',
        src_app_cd='NFM',
        entity_cd='USM',
        dept_cd='9999',
        branch_cd='100',
        gl_account='123456',
        sub_account='UNASSIGNED',
        affiliate_cd='999999',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
        cr_dr_ind='DR',
        transaction_currency='USD',
        transaction_amount=Decimal('100.00'),
        accounted_currency='USD',
        accounted_amount=Decimal('100.00'),
        fx_rate=Decimal('1.0'),
        as_of_date=BUSINESS_DT,
        business_date=BUSINESS_DT,
    )
    fields.update(overrides)
    return GLInstruction(**fields)


def _interface_row(instruction: GLInstruction) -> tuple:
    values = dict(
        WORKFLOW_RUN_ID=str(instruction.workflow_run_id),
        PRODUCER_RUN_ID=str(instruction.producer_run_id),
        DATACLASS=instruction.dataclass,
        TRANSACTION_NUMBER=instruction.transaction_number,
        LINE_NUMBER=instruction.line_number,
        ENTITY_CD=instruction.entity_cd,
        DEPT_CD=instruction.dept_cd,
        BRANCH_CD=instruction.branch_cd,
        GL_ACCOUNT=instruction.gl_account,
        SUB_ACCOUNT=instruction.sub_account,
        AFFILIATE_CD=instruction.affiliate_cd,
        PRODUCT_CD=instruction.product_cd,
        BOOK_CD=instruction.book_cd,
        SOURCE_CD=instruction.source_cd,
        CR_DR_IND=instruction.cr_dr_ind,
        FOUNDRY_RULE_ID=instruction.foundry_rule_id,
        POSTING_ID=instruction.posting_id,
        POSTING_STREAM=instruction.posting_stream,
        SRC_RECORD_ID=instruction.src_record_id,
        SRC_APP_CD=instruction.src_app_cd,
        TRANSACTION_CURRENCY=instruction.transaction_currency,
        TRANSACTION_AMOUNT=instruction.transaction_amount,
        ACCOUNTED_CURRENCY=instruction.accounted_currency,
        ACCOUNTED_AMOUNT=instruction.accounted_amount,
        FX_RATE=instruction.fx_rate,
        AS_OF_DATE=instruction.as_of_date,
        BUSINESS_DATE=instruction.business_date,
    )
    return tuple(values[name] for name in INTERFACE_TRIAL_BALANCE_SCHEMA.fieldNames())


@pytest.fixture
def run_tracker():
    return RunTracker(_FakeRunRepository())


@pytest.fixture
def registry():
    return _FakeRegistryClient(VALID_SEGMENTS)


@pytest.fixture
def gl(spark, tmp_path, registry):
    return GLClient.from_csv(
        spark=spark,
        segment_default_path='data/gl/segment_defaults.csv',
        registry=registry,
        posting_path=tmp_path / 'POSTING',
    )


@pytest.fixture
def recon(spark, tmp_path, run_tracker, gl):
    return ReconClient.from_csv(
        spark=spark,
        run_tracker=run_tracker,
        gl=gl,
        result_path=tmp_path / 'RESULT',
        interface_trial_balance_path=tmp_path / 'INTERFACE_TRIAL_BALANCE',
    )


def _seed_interface(spark, tmp_path, instructions):
    store = CsvStore(
        spark=spark,
        table_locations={
            'INTERFACE_TRIAL_BALANCE': tmp_path / 'INTERFACE_TRIAL_BALANCE',
        },
    )
    df = spark.createDataFrame(
        [_interface_row(instruction) for instruction in instructions],
        schema=INTERFACE_TRIAL_BALANCE_SCHEMA,
    )
    store.write(df, table_name='INTERFACE_TRIAL_BALANCE')


# -- balanced flow: Foundry(seeded) -> Interface -> GL -> Recon -----------

def test_balanced_interface_and_gl_population_reconciles_with_zero_differences(
    spark, tmp_path, run_tracker, gl, recon,
):
    workflow_run_id = run_tracker.start_workflow(
        dataclass='TRIAL_BALANCE', business_dt=BUSINESS_DT,
    ).workflow_run_id

    cash = _instruction(
        workflow_run_id,
        posting_id='POST-1', gl_account='123456', accounted_amount=Decimal('90000.00'),
    )
    payable = _instruction(
        workflow_run_id,
        posting_id='POST-2', gl_account='223456', accounted_amount=Decimal('-65000.00'),
        cr_dr_ind='CR',
    )

    _seed_interface(spark, tmp_path, [cash, payable])

    for instruction in (cash, payable):
        result = gl.process_instruction(instruction)
        assert result.posted, result.validation.errors

    run_result = recon.reconcile(workflow_run_id)

    assert isinstance(run_result, ReconRunResult)
    assert run_result.workflow_run_id == workflow_run_id
    assert run_result.result_count == 2
    assert run_result.break_count == 0
    assert all(r.difference_amount == Decimal('0.00') for r in run_result.results)

    # Recon rows are retrievable by workflow_run_id through a fresh
    # repository instance against the same physical store.
    verify_store = CsvStore(spark=spark, table_locations={'RESULT': tmp_path / 'RESULT'})
    persisted = ReconRepository(verify_store, spark).get_results(workflow_run_id).collect()

    assert len(persisted) == 2

    recon_executions = [
        e for e in run_tracker.get_execution_runs(workflow_run_id)
        if e.component == 'recon'
    ]
    assert len(recon_executions) == 1
    recon_execution = recon_executions[0]

    for row in persisted:
        # WORKFLOW_RUN_ID is the source workflow being reconciled;
        # PRODUCER_RUN_ID is the recon execution that produced the row --
        # never the same as GL's or Foundry's own producer_run_id.
        assert row['WORKFLOW_RUN_ID'] == str(workflow_run_id)
        assert row['PRODUCER_RUN_ID'] == str(recon_execution.run_id)
        assert row['DIFFERENCE_AMOUNT'] == Decimal('0.00')

    balances = {row['GL_ACCOUNT']: row for row in persisted}
    assert balances['123456']['INTERFACE_BALANCE'] == Decimal('90000.00')
    assert balances['123456']['GL_BALANCE'] == Decimal('90000.00')
    assert balances['223456']['INTERFACE_BALANCE'] == Decimal('-65000.00')
    assert balances['223456']['GL_BALANCE'] == Decimal('-65000.00')


# -- controlled break: a duplicated GL posting produces a real break ------

def test_a_duplicated_gl_posting_produces_a_non_zero_difference(
    spark, tmp_path, run_tracker, gl, recon,
):
    workflow_run_id = run_tracker.start_workflow(
        dataclass='TRIAL_BALANCE', business_dt=BUSINESS_DT,
    ).workflow_run_id

    instruction = _instruction(
        workflow_run_id,
        posting_id='POST-3', gl_account='123456', accounted_amount=Decimal('500.00'),
    )

    _seed_interface(spark, tmp_path, [instruction])

    # Foundry/Interface produced exactly one accounting instruction, but
    # GL erroneously posts it twice -- the "duplicated posting" break
    # scenario named in docs/northforge_finance_data_model.md section 21.
    for _ in range(2):
        result = gl.process_instruction(instruction)
        assert result.posted, result.validation.errors

    run_result = recon.reconcile(workflow_run_id)

    assert run_result.result_count == 1
    assert run_result.break_count == 1

    [balance] = run_result.results
    assert balance.interface_balance == Decimal('500.00')
    assert balance.gl_balance == Decimal('1000.00')
    assert balance.difference_amount == Decimal('-500.00')

    verify_store = CsvStore(spark=spark, table_locations={'RESULT': tmp_path / 'RESULT'})
    [row] = ReconRepository(verify_store, spark).get_results(workflow_run_id).collect()
    assert row['DIFFERENCE_AMOUNT'] == Decimal('-500.00')


# -- workflow scoping across multiple recon executions in one store -------

def test_recon_results_from_different_workflows_stay_isolated_in_the_shared_store(
    spark, tmp_path, run_tracker, gl, recon,
):
    balanced_workflow_run_id = run_tracker.start_workflow(
        dataclass='TRIAL_BALANCE', business_dt=BUSINESS_DT,
    ).workflow_run_id
    broken_workflow_run_id = run_tracker.start_workflow(
        dataclass='TRIAL_BALANCE', business_dt=BUSINESS_DT,
    ).workflow_run_id

    balanced_instruction = _instruction(
        balanced_workflow_run_id, posting_id='POST-4', accounted_amount=Decimal('42.00'),
    )
    broken_instruction = _instruction(
        broken_workflow_run_id, posting_id='POST-5', accounted_amount=Decimal('10.00'),
    )

    _seed_interface(spark, tmp_path, [balanced_instruction, broken_instruction])

    gl.process_instruction(balanced_instruction)
    gl.process_instruction(broken_instruction)
    gl.process_instruction(broken_instruction)  # duplicate -> break

    balanced_result = recon.reconcile(balanced_workflow_run_id)
    broken_result = recon.reconcile(broken_workflow_run_id)

    assert balanced_result.break_count == 0
    assert broken_result.break_count == 1

    verify_store = CsvStore(spark=spark, table_locations={'RESULT': tmp_path / 'RESULT'})
    repository = ReconRepository(verify_store, spark)

    balanced_rows = repository.get_results(balanced_workflow_run_id).collect()
    broken_rows = repository.get_results(broken_workflow_run_id).collect()

    assert {row['WORKFLOW_RUN_ID'] for row in balanced_rows} == {str(balanced_workflow_run_id)}
    assert {row['WORKFLOW_RUN_ID'] for row in broken_rows} == {str(broken_workflow_run_id)}
