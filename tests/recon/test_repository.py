from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from pyspark.sql import DataFrame

from core.store import CsvStore

from recon.models import ReconResult
from recon.repository import ReconRepository


def _result(**overrides) -> ReconResult:
    fields = dict(
        recon_result_id=uuid4(),
        reconciled_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        workflow_run_id=uuid4(),
        producer_run_id=uuid4(),
        as_of_date=date(2026, 1, 1),
        entity_cd='USM',
        dept_cd='4000',
        branch_cd='100',
        gl_account='123456',
        sub_account='001',
        affiliate_cd='AFF1',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
        accounted_currency='USD',
        interface_balance=Decimal('100.00'),
        gl_balance=Decimal('100.00'),
        difference_amount=Decimal('0.00'),
    )
    fields.update(overrides)
    return ReconResult(**fields)


@pytest.fixture
def repository(spark, tmp_path):
    store = CsvStore(
        spark=spark,
        table_locations={
            'RESULT': tmp_path / 'RESULT',
        },
    )
    return ReconRepository(store, spark)


def test_get_results_returns_a_spark_dataframe(repository):
    repository.write_results([_result()])

    result = repository.get_results(uuid4())

    assert isinstance(result, DataFrame)


def test_write_results_persists_all_fields(repository):
    result = _result()

    repository.write_results([result])

    rows = repository.get_results(result.workflow_run_id).collect()

    assert len(rows) == 1
    row = rows[0]
    assert UUID(row['RECON_RESULT_ID']) == result.recon_result_id
    assert UUID(row['WORKFLOW_RUN_ID']) == result.workflow_run_id
    assert UUID(row['PRODUCER_RUN_ID']) == result.producer_run_id
    assert row['AS_OF_DATE'] == result.as_of_date
    assert row['ENTITY_CD'] == result.entity_cd
    assert row['DEPT_CD'] == result.dept_cd
    assert row['BRANCH_CD'] == result.branch_cd
    assert row['GL_ACCOUNT'] == result.gl_account
    assert row['SUB_ACCOUNT'] == result.sub_account
    assert row['AFFILIATE_CD'] == result.affiliate_cd
    assert row['PRODUCT_CD'] == result.product_cd
    assert row['BOOK_CD'] == result.book_cd
    assert row['SOURCE_CD'] == result.source_cd
    assert row['ACCOUNTED_CURRENCY'] == result.accounted_currency
    assert row['INTERFACE_BALANCE'] == result.interface_balance
    assert row['GL_BALANCE'] == result.gl_balance
    assert row['DIFFERENCE_AMOUNT'] == result.difference_amount


def test_write_results_persists_multiple_rows_in_one_call(repository):
    workflow_run_id = uuid4()
    first = _result(workflow_run_id=workflow_run_id, gl_account='111111')
    second = _result(workflow_run_id=workflow_run_id, gl_account='222222')

    repository.write_results([first, second])

    rows = repository.get_results(workflow_run_id).collect()

    assert {row['GL_ACCOUNT'] for row in rows} == {'111111', '222222'}


def test_write_results_with_empty_sequence_is_a_no_op(repository):
    repository.write_results([])

    assert repository.get_results(uuid4()).collect() == []


def test_get_results_returns_only_the_named_workflows_rows(repository):
    kept = _result()
    other = _result(as_of_date=kept.as_of_date)

    repository.write_results([kept, other])

    rows = repository.get_results(kept.workflow_run_id).collect()

    assert len(rows) == 1
    assert UUID(rows[0]['WORKFLOW_RUN_ID']) == kept.workflow_run_id


def test_get_results_returns_rows_from_multiple_producer_runs_under_the_same_workflow(
    repository,
):
    # WORKFLOW_RUN_ID is the operational read key: rows sharing a
    # WORKFLOW_RUN_ID but carrying different PRODUCER_RUN_IDs (e.g. a
    # re-run of recon under the same workflow) are still both selected
    # together.
    shared_workflow_run_id = uuid4()

    r1 = _result(workflow_run_id=shared_workflow_run_id)
    r2 = _result(workflow_run_id=shared_workflow_run_id)

    repository.write_results([r1, r2])

    rows = repository.get_results(shared_workflow_run_id).collect()

    assert {UUID(r['RECON_RESULT_ID']) for r in rows} == {
        r1.recon_result_id, r2.recon_result_id,
    }
    assert {UUID(r['PRODUCER_RUN_ID']) for r in rows} == {
        r1.producer_run_id, r2.producer_run_id,
    }


def test_get_results_excludes_rows_from_other_workflows(repository):
    kept_workflow_run_id = uuid4()
    other_workflow_run_id = uuid4()

    repository.write_results([
        _result(workflow_run_id=kept_workflow_run_id),
        _result(workflow_run_id=other_workflow_run_id),
    ])

    rows = repository.get_results(kept_workflow_run_id).collect()

    assert len(rows) == 1
    assert UUID(rows[0]['WORKFLOW_RUN_ID']) == kept_workflow_run_id


def test_write_results_preserves_decimal_precision(repository):
    result = _result(
        interface_balance=Decimal('12345.123456789012'),
        gl_balance=Decimal('12345.123456789000'),
        difference_amount=Decimal('0.000000000012'),
    )

    repository.write_results([result])

    row = repository.get_results(result.workflow_run_id).collect()[0]

    assert row['INTERFACE_BALANCE'] == Decimal('12345.123456789012')
    assert row['GL_BALANCE'] == Decimal('12345.123456789000')
    assert row['DIFFERENCE_AMOUNT'] == Decimal('0.000000000012')
    assert isinstance(row['DIFFERENCE_AMOUNT'], Decimal)


def test_write_results_preserves_negative_difference_amount(repository):
    result = _result(difference_amount=Decimal('-500.00'))

    repository.write_results([result])

    row = repository.get_results(result.workflow_run_id).collect()[0]

    assert row['DIFFERENCE_AMOUNT'] == Decimal('-500.00')


class _FakeStore:
    """A minimal Store stand-in, to prove ReconRepository is backend-agnostic."""

    def __init__(self, tables):
        self._tables = tables

    def read(self, table_name, schema=None):
        return self._tables[table_name]

    def write(self, df, table_name, mode='append'):
        self._tables[table_name] = df


def test_get_results_works_against_a_fake_store(spark):
    workflow_run_id = uuid4()
    result = _result(workflow_run_id=workflow_run_id)

    store = _FakeStore({})
    repository = ReconRepository(store, spark)

    repository.write_results([result])
    rows = repository.get_results(workflow_run_id).collect()

    assert len(rows) == 1
    assert rows[0]['GL_ACCOUNT'] == result.gl_account
