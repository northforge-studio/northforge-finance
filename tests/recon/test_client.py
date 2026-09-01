from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from core.store import CsvStore
from core.runs import RunRepository, RunTracker

from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA, POSTING_SCHEMA

from recon import ReconClient
from recon.models import ReconRunResult
from recon.repository import ReconRepository


BUSINESS_DT = date(2026, 1, 1)


class _FakeRunRepository(RunRepository):
    """Mirrors tests/workflow/test_orchestrator.py's in-memory RunRepository
    stand-in, so RunTracker (the real collaborator) can run without a
    database."""

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


class _FakeGL:
    def __init__(self, postings_by_workflow):
        self._postings_by_workflow = postings_by_workflow


    def get_postings(self, workflow_run_id):
        return self._postings_by_workflow[workflow_run_id]


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
        POSTED_AT=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
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


@pytest.fixture
def run_tracker():
    return RunTracker(_FakeRunRepository())


@pytest.fixture
def workflow(run_tracker):
    return run_tracker.start_workflow(dataclass='TRIAL_BALANCE', business_dt=BUSINESS_DT)


def test_from_csv_reconciles_and_persists_through_a_real_repository(
    spark, tmp_path, run_tracker, workflow,
):
    interface_store = CsvStore(
        spark=spark,
        table_locations={
            'INTERFACE_TRIAL_BALANCE': tmp_path / 'INTERFACE_TRIAL_BALANCE',
        },
    )
    interface_df = spark.createDataFrame(
        [_interface_values(workflow.workflow_run_id)],
        schema=INTERFACE_TRIAL_BALANCE_SCHEMA,
    )
    interface_store.write(interface_df, table_name='INTERFACE_TRIAL_BALANCE')

    gl_df = spark.createDataFrame(
        [_posting_values(workflow.workflow_run_id)],
        schema=POSTING_SCHEMA,
    )
    gl = _FakeGL({workflow.workflow_run_id: gl_df})

    client = ReconClient.from_csv(
        spark=spark,
        run_tracker=run_tracker,
        gl=gl,
        result_path=tmp_path / 'RESULT',
        interface_trial_balance_path=tmp_path / 'INTERFACE_TRIAL_BALANCE',
    )

    result = client.reconcile(workflow.workflow_run_id)

    assert isinstance(result, ReconRunResult)
    assert result.result_count == 1
    assert result.break_count == 0

    # Read back through a fresh ReconRepository against the same CSV
    # store, to prove the client's write actually reached persistence.
    verify_store = CsvStore(
        spark=spark,
        table_locations={'RESULT': tmp_path / 'RESULT'},
    )
    persisted = ReconRepository(verify_store, spark).get_results(
        workflow.workflow_run_id
    ).collect()

    assert len(persisted) == 1
    assert persisted[0]['WORKFLOW_RUN_ID'] == str(workflow.workflow_run_id)
    assert persisted[0]['PRODUCER_RUN_ID'] == str(result.producer_run_id)
    assert persisted[0]['DIFFERENCE_AMOUNT'] == Decimal('0.00')

    # The client's own get_results() (not just a fresh ReconRepository)
    # reads back the same persisted row.
    via_client = client.get_results(workflow.workflow_run_id).collect()
    assert len(via_client) == 1
    assert via_client[0]['WORKFLOW_RUN_ID'] == str(workflow.workflow_run_id)


def test_reconcile_raises_for_an_unsupported_dataclass(spark, tmp_path, run_tracker):
    workflow = run_tracker.start_workflow(dataclass='POSITION', business_dt=BUSINESS_DT)

    client = ReconClient.from_csv(
        spark=spark,
        run_tracker=run_tracker,
        gl=_FakeGL({}),
        result_path=tmp_path / 'RESULT',
        interface_trial_balance_path=tmp_path / 'INTERFACE_TRIAL_BALANCE',
    )

    with pytest.raises(ValueError, match='POSITION'):
        client.reconcile(workflow.workflow_run_id)
