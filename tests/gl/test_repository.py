from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from pyspark.sql import DataFrame

from core.store import CsvStore

from registry.models import SegmentType

from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA
from gl.models import (
    GLInstruction, 
    GLPosting, 
    GLRejection, 
    SegmentDefault, 
    SegmentDefaults
)
from gl.repository import GLRepository


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            'SEGMENT_DEFAULT': 'data/gl/segment_default.csv',
        },
    )
    return GLRepository(store, spark)


def test_get_segment_default_returns_contextual_default(repository):
    result = repository.get_segment_default(SegmentType.DEPARTMENT, 'ENTITY_CD', 'USMKTS')

    assert result == SegmentDefault(
        segment_type=SegmentType.DEPARTMENT,
        context_type='ENTITY_CD',
        context_value='USMKTS',
        default_value='USGL99',
    )


def test_get_segment_default_returns_global_default(repository):
    result = repository.get_segment_default(SegmentType.SUB_ACCOUNT, '*', '*')

    assert result == SegmentDefault(
        segment_type=SegmentType.SUB_ACCOUNT,
        context_type='*',
        context_value='*',
        default_value='990001',
    )


def test_get_segment_default_returns_none_for_unknown_combination(repository):
    result = repository.get_segment_default(SegmentType.DEPARTMENT, 'ENTITY_CD', 'UNKNOWN')

    assert result is None


def test_get_segment_default_does_not_fall_back_from_contextual_request_to_global_row(
    repository,
):
    # AFFILIATE_CD only has a global (*, *) row configured.
    result = repository.get_segment_default(SegmentType.AFFILIATE, 'ENTITY_CD', 'USMKTS')

    assert result is None


def test_get_segment_default_does_not_fall_back_from_global_request_to_contextual_row(
    repository,
):
    # DEPT_CD only has ENTITY_CD-contextual rows configured.
    result = repository.get_segment_default(SegmentType.DEPARTMENT, '*', '*')

    assert result is None


def test_get_segment_default_preserves_numeric_looking_values_as_strings(repository):
    result = repository.get_segment_default(SegmentType.ACCOUNT, 'ENTITY_CD', 'USMKTS')

    assert result.default_value == '990101'
    assert isinstance(result.default_value, str)


class _FakeStore:
    """A minimal Store stand-in, to prove GLRepository is backend-agnostic."""

    def __init__(self, tables):
        self._tables = tables

    def read(self, table_name, schema=None):
        return self._tables[table_name]


def test_get_segment_default_works_against_a_fake_store(spark):
    df = spark.createDataFrame(
        [
            ('DEPT_CD', 'ENTITY_CD', 'ZZZ', '0099'),
        ],
        ['SEGMENT_TYPE', 'CONTEXT_TYPE', 'CONTEXT_VALUE', 'DEFAULT_VALUE'],
    )

    store = _FakeStore({'SEGMENT_DEFAULT': df})
    repository = GLRepository(store, spark)

    result = repository.get_segment_default(SegmentType.DEPARTMENT, 'ENTITY_CD', 'ZZZ')

    assert result.default_value == '0099'
    assert isinstance(result.default_value, str)


# -- write_posting / get_postings ----------------------------------------

def _posting(**overrides) -> GLPosting:
    fields = dict(
        gl_posting_id=uuid4(),
        posted_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        workflow_run_id=uuid4(),
        producer_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        transaction_number='TXN-1',
        line_number='1',
        foundry_rule_id='RULE-1',
        posting_id='POST-1',
        posting_stream='STREAM-1',
        src_record_id='REC-1',
        src_app_cd='NFM',
        entity_cd='USM',
        dept_cd='4000',
        branch_cd='100',
        gl_account='123456',
        sub_account='001',
        affiliate_cd='AFF1',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
        cr_dr_ind='DR',
        transaction_currency='USD',
        transaction_amount=Decimal('100.00'),
        accounted_currency='USD',
        accounted_amount=Decimal('100.00'),
        fx_rate=Decimal('1.0'),
        as_of_date=date(2026, 1, 1),
        business_date=date(2026, 1, 1),
    )
    fields.update(overrides)
    return GLPosting(**fields)


@pytest.fixture
def posting_repository(spark, tmp_path):
    store = CsvStore(
        spark=spark,
        table_locations={
            'POSTING': tmp_path / 'POSTING',
        },
    )
    return GLRepository(store, spark)


def test_get_postings_returns_a_spark_dataframe(posting_repository):
    posting_repository.write_posting(_posting())

    result = posting_repository.get_postings(uuid4())

    assert isinstance(result, DataFrame)


def test_write_posting_persists_all_lineage_and_accounting_fields(posting_repository):
    posting = _posting()

    posting_repository.write_posting(posting)

    rows = posting_repository.get_postings(posting.workflow_run_id).collect()

    assert len(rows) == 1
    row = rows[0]
    assert UUID(row['GL_POSTING_ID']) == posting.gl_posting_id
    assert UUID(row['WORKFLOW_RUN_ID']) == posting.workflow_run_id
    assert UUID(row['PRODUCER_RUN_ID']) == posting.producer_run_id
    assert row['DATACLASS'] == posting.dataclass
    assert row['TRANSACTION_NUMBER'] == posting.transaction_number
    assert row['LINE_NUMBER'] == posting.line_number
    assert row['FOUNDRY_RULE_ID'] == posting.foundry_rule_id
    assert row['POSTING_ID'] == posting.posting_id
    assert row['POSTING_STREAM'] == posting.posting_stream
    assert row['SRC_RECORD_ID'] == posting.src_record_id
    assert row['SRC_APP_CD'] == posting.src_app_cd
    assert row['CR_DR_IND'] == posting.cr_dr_ind
    assert row['TRANSACTION_CURRENCY'] == posting.transaction_currency
    assert row['TRANSACTION_AMOUNT'] == posting.transaction_amount
    assert row['ACCOUNTED_CURRENCY'] == posting.accounted_currency
    assert row['ACCOUNTED_AMOUNT'] == posting.accounted_amount
    assert row['FX_RATE'] == posting.fx_rate
    assert row['AS_OF_DATE'] == posting.as_of_date
    assert row['BUSINESS_DATE'] == posting.business_date


def test_write_posting_persists_resolved_gl_segments(posting_repository):
    posting = _posting(
        entity_cd='USM',
        dept_cd='9999',
        branch_cd='9999',
        gl_account='999999',
        sub_account='UNASSIGNED',
        affiliate_cd='999999',
        product_cd='999999',
        book_cd='US_DEFAULT',
        source_cd='SRC1',
    )

    posting_repository.write_posting(posting)

    row = posting_repository.get_postings(posting.workflow_run_id).collect()[0]

    assert row['ENTITY_CD'] == 'USM'
    assert row['DEPT_CD'] == '9999'
    assert row['BRANCH_CD'] == '9999'
    assert row['GL_ACCOUNT'] == '999999'
    assert row['SUB_ACCOUNT'] == 'UNASSIGNED'
    assert row['AFFILIATE_CD'] == '999999'
    assert row['PRODUCT_CD'] == '999999'
    assert row['BOOK_CD'] == 'US_DEFAULT'
    assert row['SOURCE_CD'] == 'SRC1'


def test_get_postings_returns_only_the_named_workflows_rows(posting_repository):
    # The same business_dt can be processed by multiple GL workflows.
    # get_postings must isolate a single workflow's output by
    # workflow_run_id, never by business_dt.
    kept = _posting()
    other = _posting(business_date=kept.business_date)

    posting_repository.write_posting(kept)
    posting_repository.write_posting(other)

    rows = posting_repository.get_postings(kept.workflow_run_id).collect()

    assert len(rows) == 1
    assert UUID(rows[0]['WORKFLOW_RUN_ID']) == kept.workflow_run_id


def test_get_postings_returns_rows_from_multiple_producer_runs_under_the_same_workflow(
    posting_repository,
):
    # V1 has exactly one producer execution per workflow for a given
    # output table, but WORKFLOW_RUN_ID (not PRODUCER_RUN_ID) is the
    # operational read key. This makes that lookup semantic explicit:
    # rows sharing a WORKFLOW_RUN_ID but carrying different
    # PRODUCER_RUN_IDs are still both selected together.
    shared_workflow_run_id = uuid4()

    g1 = _posting(workflow_run_id=shared_workflow_run_id)
    g2 = _posting(workflow_run_id=shared_workflow_run_id)

    posting_repository.write_posting(g1)
    posting_repository.write_posting(g2)

    rows = posting_repository.get_postings(shared_workflow_run_id).collect()

    assert {UUID(r['GL_POSTING_ID']) for r in rows} == {g1.gl_posting_id, g2.gl_posting_id}
    assert {UUID(r['PRODUCER_RUN_ID']) for r in rows} == {
        g1.producer_run_id, g2.producer_run_id,
    }


def test_get_postings_excludes_rows_from_other_workflows(posting_repository):
    kept_workflow_run_id = uuid4()
    other_workflow_run_id = uuid4()

    posting_repository.write_posting(_posting(workflow_run_id=kept_workflow_run_id))
    posting_repository.write_posting(_posting(workflow_run_id=other_workflow_run_id))

    rows = posting_repository.get_postings(kept_workflow_run_id).collect()

    assert len(rows) == 1
    assert UUID(rows[0]['WORKFLOW_RUN_ID']) == kept_workflow_run_id


def test_get_postings_allows_more_than_one_row_for_same_posting_id(posting_repository):
    workflow_run_id = uuid4()
    first = _posting(gl_posting_id=uuid4(), posting_id='DUP', workflow_run_id=workflow_run_id)
    second = _posting(gl_posting_id=uuid4(), posting_id='DUP', workflow_run_id=workflow_run_id)

    posting_repository.write_posting(first)
    posting_repository.write_posting(second)

    rows = posting_repository.get_postings(workflow_run_id).collect()

    assert len(rows) == 2
    assert {row['POSTING_ID'] for row in rows} == {'DUP'}
    assert {UUID(row['GL_POSTING_ID']) for row in rows} == {
        first.gl_posting_id,
        second.gl_posting_id,
    }


def test_write_posting_preserves_decimal_precision(posting_repository):
    posting = _posting(
        transaction_amount=Decimal('12345.123456789012'),
        fx_rate=Decimal('1.123456789012'),
    )

    posting_repository.write_posting(posting)

    row = posting_repository.get_postings(posting.workflow_run_id).collect()[0]

    assert row['TRANSACTION_AMOUNT'] == Decimal('12345.123456789012')
    assert row['FX_RATE'] == Decimal('1.123456789012')
    assert isinstance(row['FX_RATE'], Decimal)


# -- write_rejection / get_rejections -------------------------------------

def _rejection(**overrides) -> GLRejection:
    fields = dict(
        gl_rejection_id=uuid4(),
        rejected_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        workflow_run_id=uuid4(),
        producer_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        transaction_number='TXN-1',
        line_number='1',
        foundry_rule_id='RULE-1',
        posting_id='POST-1',
        posting_stream='STREAM-1',
        src_record_id='REC-1',
        src_app_cd='NFM',
        business_date=date(2026, 1, 1),
        as_of_date=date(2026, 1, 1),
        rejection_type='STRUCTURAL_VALIDATION',
        rejection_detail='MISSING_POSTING_ID',
    )
    fields.update(overrides)
    return GLRejection(**fields)


@pytest.fixture
def rejection_repository(spark, tmp_path):
    store = CsvStore(
        spark=spark,
        table_locations={
            'REJECTION': tmp_path / 'REJECTION',
        },
    )
    return GLRepository(store, spark)


def test_get_rejections_returns_a_spark_dataframe(rejection_repository):
    rejection_repository.write_rejection(_rejection())

    result = rejection_repository.get_rejections(uuid4())

    assert isinstance(result, DataFrame)


def test_write_rejection_persists_lineage_and_diagnostics(rejection_repository):
    rejection = _rejection()

    rejection_repository.write_rejection(rejection)

    rows = rejection_repository.get_rejections(rejection.workflow_run_id).collect()

    assert len(rows) == 1
    row = rows[0]
    assert UUID(row['GL_REJECTION_ID']) == rejection.gl_rejection_id
    assert UUID(row['WORKFLOW_RUN_ID']) == rejection.workflow_run_id
    assert UUID(row['PRODUCER_RUN_ID']) == rejection.producer_run_id
    assert row['DATACLASS'] == rejection.dataclass
    assert row['TRANSACTION_NUMBER'] == rejection.transaction_number
    assert row['LINE_NUMBER'] == rejection.line_number
    assert row['FOUNDRY_RULE_ID'] == rejection.foundry_rule_id
    assert row['POSTING_ID'] == rejection.posting_id
    assert row['POSTING_STREAM'] == rejection.posting_stream
    assert row['SRC_RECORD_ID'] == rejection.src_record_id
    assert row['SRC_APP_CD'] == rejection.src_app_cd
    assert row['BUSINESS_DATE'] == rejection.business_date
    assert row['AS_OF_DATE'] == rejection.as_of_date
    assert row['REJECTION_TYPE'] == rejection.rejection_type
    assert row['REJECTION_DETAIL'] == rejection.rejection_detail


def test_write_rejection_stores_segment_resolution_rejection_type(rejection_repository):
    rejection = _rejection(
        rejection_type='SEGMENT_RESOLUTION',
        rejection_detail='DEPT_CD,BRANCH_CD',
    )

    rejection_repository.write_rejection(rejection)

    row = rejection_repository.get_rejections(rejection.workflow_run_id).collect()[0]

    assert row['REJECTION_TYPE'] == 'SEGMENT_RESOLUTION'
    assert row['REJECTION_DETAIL'] == 'DEPT_CD,BRANCH_CD'


def test_get_rejections_returns_only_the_named_workflows_rows(rejection_repository):
    # Same regression scenario as postings: the same business_dt can be
    # processed by multiple GL workflows, so business_dt must never be
    # the selector for a specific workflow's rejections.
    kept = _rejection()
    other = _rejection(business_date=kept.business_date)

    rejection_repository.write_rejection(kept)
    rejection_repository.write_rejection(other)

    rows = rejection_repository.get_rejections(kept.workflow_run_id).collect()

    assert len(rows) == 1
    assert UUID(rows[0]['WORKFLOW_RUN_ID']) == kept.workflow_run_id


def test_get_rejections_returns_rows_from_multiple_producer_runs_under_the_same_workflow(
    rejection_repository,
):
    # Same lookup semantics as postings: WORKFLOW_RUN_ID is the
    # operational key, so rows sharing a WORKFLOW_RUN_ID but carrying
    # different PRODUCER_RUN_IDs are still both selected together.
    shared_workflow_run_id = uuid4()

    g1 = _rejection(workflow_run_id=shared_workflow_run_id)
    g2 = _rejection(workflow_run_id=shared_workflow_run_id)

    rejection_repository.write_rejection(g1)
    rejection_repository.write_rejection(g2)

    rows = rejection_repository.get_rejections(shared_workflow_run_id).collect()

    assert {UUID(r['GL_REJECTION_ID']) for r in rows} == {g1.gl_rejection_id, g2.gl_rejection_id}
    assert {UUID(r['PRODUCER_RUN_ID']) for r in rows} == {
        g1.producer_run_id, g2.producer_run_id,
    }


def test_get_rejections_excludes_rows_from_other_workflows(rejection_repository):
    kept_workflow_run_id = uuid4()
    other_workflow_run_id = uuid4()

    rejection_repository.write_rejection(_rejection(workflow_run_id=kept_workflow_run_id))
    rejection_repository.write_rejection(_rejection(workflow_run_id=other_workflow_run_id))

    rows = rejection_repository.get_rejections(kept_workflow_run_id).collect()

    assert len(rows) == 1
    assert UUID(rows[0]['WORKFLOW_RUN_ID']) == kept_workflow_run_id


# -- get_instructions -------------------------------------------------------

WORKFLOW_RUN_ID = uuid4()
PRODUCER_RUN_ID = uuid4()


def _instruction(**overrides) -> GLInstruction:
    fields = dict(
        workflow_run_id=WORKFLOW_RUN_ID,
        producer_run_id=PRODUCER_RUN_ID,
        dataclass='TRIAL_BALANCE',
        transaction_number='TXN-1',
        line_number='1',
        foundry_rule_id='RULE-1',
        posting_id='POST-1',
        posting_stream='STREAM-1',
        src_record_id='REC-1',
        src_app_cd='NFM',
        entity_cd='USM',
        dept_cd='4000',
        branch_cd='100',
        gl_account='123456',
        sub_account='001',
        affiliate_cd='AFF1',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
        cr_dr_ind='DR',
        transaction_currency='USD',
        transaction_amount=Decimal('100.00'),
        accounted_currency='USD',
        accounted_amount=Decimal('100.00'),
        fx_rate=Decimal('1.0'),
        as_of_date=date(2026, 1, 1),
        business_date=date(2026, 1, 1),
    )
    fields.update(overrides)
    return GLInstruction(**fields)


@pytest.fixture
def interface_repository(spark, tmp_path):
    store = CsvStore(
        spark=spark,
        table_locations={
            'INTERFACE_TRIAL_BALANCE': tmp_path / 'INTERFACE_TRIAL_BALANCE',
        },
    )
    return GLRepository(store, spark)


def _write_instruction_row(repository, instruction: GLInstruction) -> None:
    row = (
        str(instruction.workflow_run_id),
        str(instruction.producer_run_id),
        instruction.dataclass,
        instruction.transaction_number,
        instruction.line_number,
        instruction.entity_cd,
        instruction.branch_cd,
        instruction.dept_cd,
        instruction.gl_account,
        instruction.sub_account,
        instruction.affiliate_cd,
        instruction.product_cd,
        instruction.book_cd,
        instruction.source_cd,
        instruction.cr_dr_ind,
        instruction.foundry_rule_id,
        instruction.posting_id,
        instruction.posting_stream,
        instruction.src_record_id,
        instruction.src_app_cd,
        instruction.transaction_currency,
        instruction.transaction_amount,
        instruction.accounted_currency,
        instruction.accounted_amount,
        instruction.fx_rate,
        instruction.as_of_date,
        instruction.business_date,
    )

    df = repository._spark.createDataFrame([row], schema=INTERFACE_TRIAL_BALANCE_SCHEMA)
    repository._store.write(df, table_name='INTERFACE_TRIAL_BALANCE')


def test_get_instructions_returns_correct_partition(interface_repository):
    _write_instruction_row(interface_repository, _instruction())

    results = interface_repository.get_instructions(WORKFLOW_RUN_ID)

    assert len(results) == 1
    assert results[0].transaction_number == 'TXN-1'
    assert results[0].workflow_run_id == WORKFLOW_RUN_ID
    assert results[0].producer_run_id == PRODUCER_RUN_ID


def test_get_instructions_excludes_other_workflow_runs(interface_repository):
    other_workflow_run_id = uuid4()
    _write_instruction_row(interface_repository, _instruction())
    _write_instruction_row(
        interface_repository,
        _instruction(workflow_run_id=other_workflow_run_id),
    )

    results = interface_repository.get_instructions(WORKFLOW_RUN_ID)

    assert len(results) == 1
    assert results[0].workflow_run_id == WORKFLOW_RUN_ID


def test_get_instructions_returns_rows_from_multiple_producer_runs_under_the_same_workflow(
    interface_repository,
):
    # WORKFLOW_RUN_ID is the operational key: rows sharing a
    # WORKFLOW_RUN_ID but carrying different PRODUCER_RUN_IDs are still
    # both selected together.
    other_producer_run_id = uuid4()
    _write_instruction_row(interface_repository, _instruction())
    _write_instruction_row(
        interface_repository,
        _instruction(producer_run_id=other_producer_run_id),
    )

    results = interface_repository.get_instructions(WORKFLOW_RUN_ID)

    assert len(results) == 2
    assert {r.producer_run_id for r in results} == {PRODUCER_RUN_ID, other_producer_run_id}


def test_get_instructions_maps_all_fields(interface_repository):
    instruction = _instruction()
    _write_instruction_row(interface_repository, instruction)

    result = interface_repository.get_instructions(WORKFLOW_RUN_ID)[0]

    assert result.workflow_run_id == instruction.workflow_run_id
    assert result.producer_run_id == instruction.producer_run_id
    assert isinstance(result.workflow_run_id, type(instruction.workflow_run_id))
    assert result.dataclass == instruction.dataclass
    assert result.transaction_number == instruction.transaction_number
    assert result.line_number == instruction.line_number
    assert result.foundry_rule_id == instruction.foundry_rule_id
    assert result.posting_id == instruction.posting_id
    assert result.posting_stream == instruction.posting_stream
    assert result.src_record_id == instruction.src_record_id
    assert result.src_app_cd == instruction.src_app_cd
    assert result.entity_cd == instruction.entity_cd
    assert result.dept_cd == instruction.dept_cd
    assert result.branch_cd == instruction.branch_cd
    assert result.gl_account == instruction.gl_account
    assert result.sub_account == instruction.sub_account
    assert result.affiliate_cd == instruction.affiliate_cd
    assert result.product_cd == instruction.product_cd
    assert result.book_cd == instruction.book_cd
    assert result.source_cd == instruction.source_cd
    assert result.cr_dr_ind == instruction.cr_dr_ind
    assert result.transaction_currency == instruction.transaction_currency
    assert result.transaction_amount == instruction.transaction_amount
    assert isinstance(result.transaction_amount, Decimal)
    assert result.accounted_currency == instruction.accounted_currency
    assert result.accounted_amount == instruction.accounted_amount
    assert result.fx_rate == instruction.fx_rate
    assert result.as_of_date == instruction.as_of_date
    assert result.business_date == instruction.business_date


def test_get_instructions_orders_deterministically(interface_repository):
    _write_instruction_row(
        interface_repository,
        _instruction(transaction_number='TXN-2', line_number='1', posting_id='POST-A'),
    )
    _write_instruction_row(
        interface_repository,
        _instruction(transaction_number='TXN-1', line_number='2', posting_id='POST-B'),
    )
    _write_instruction_row(
        interface_repository,
        _instruction(transaction_number='TXN-1', line_number='1', posting_id='POST-C'),
    )

    results = interface_repository.get_instructions(WORKFLOW_RUN_ID)

    assert [(r.transaction_number, r.line_number) for r in results] == [
        ('TXN-1', '1'),
        ('TXN-1', '2'),
        ('TXN-2', '1'),
    ]


# -- rollback (delete_postings / delete_rejections) -------------------------

@pytest.fixture
def posting_and_rejection_repository(spark, tmp_path):
    store = CsvStore(
        spark=spark,
        table_locations={
            'POSTING': tmp_path / 'POSTING',
            'REJECTION': tmp_path / 'REJECTION',
        },
    )
    return GLRepository(store, spark)


def test_delete_postings_removes_only_rows_for_the_named_workflow_run(
    posting_and_rejection_repository,
):
    kept_workflow_run_id = uuid4()
    deleted_workflow_run_id = uuid4()

    posting_and_rejection_repository.write_posting(
        _posting(workflow_run_id=kept_workflow_run_id)
    )
    posting_and_rejection_repository.write_posting(
        _posting(workflow_run_id=deleted_workflow_run_id)
    )

    posting_and_rejection_repository.delete_postings(deleted_workflow_run_id)

    # The targeted workflow's rows are actually gone...
    assert posting_and_rejection_repository.get_postings(deleted_workflow_run_id).collect() == []

    # ...and the other workflow's rows are untouched.
    remaining = posting_and_rejection_repository.get_postings(kept_workflow_run_id).collect()
    assert {UUID(row['WORKFLOW_RUN_ID']) for row in remaining} == {kept_workflow_run_id}


def test_delete_rejections_removes_only_rows_for_the_named_workflow_run(
    posting_and_rejection_repository,
):
    kept_workflow_run_id = uuid4()
    deleted_workflow_run_id = uuid4()

    posting_and_rejection_repository.write_rejection(
        _rejection(workflow_run_id=kept_workflow_run_id)
    )
    posting_and_rejection_repository.write_rejection(
        _rejection(workflow_run_id=deleted_workflow_run_id)
    )

    posting_and_rejection_repository.delete_rejections(deleted_workflow_run_id)

    assert posting_and_rejection_repository.get_rejections(deleted_workflow_run_id).collect() == []

    remaining = posting_and_rejection_repository.get_rejections(kept_workflow_run_id).collect()
    assert {UUID(row['WORKFLOW_RUN_ID']) for row in remaining} == {kept_workflow_run_id}


def test_resolve_prefers_entity_default():
    defaults = SegmentDefaults(
        values=(
            SegmentDefault(
                SegmentType.ACCOUNT,
                'GLOBAL',
                '*',
                '999999',
            ),
            SegmentDefault(
                SegmentType.ACCOUNT,
                'ENTITY_CD',
                'USMKTS',
                '990101',
            ),
        )
    )

    assert defaults.resolve(
        SegmentType.ACCOUNT,
        entity_cd='USMKTS',
    ) == '990101'


def test_resolve_falls_back_to_global():
    defaults = SegmentDefaults(
        values=(
            SegmentDefault(
                SegmentType.ACCOUNT,
                'GLOBAL',
                '*',
                '999999',
            ),
        )
    )

    assert defaults.resolve(
        SegmentType.ACCOUNT,
        entity_cd='CAMKTS',
    ) == '999999'


def test_resolve_returns_none_when_no_default():
    defaults = SegmentDefaults(values=())

    assert defaults.resolve(
        SegmentType.ACCOUNT,
        entity_cd='USMKTS',
    ) is None
