from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from core.store import CsvStore

from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA
from gl.models import GLInstruction, GLPosting, GLRejection, SegmentDefault
from gl.repository import GLRepository


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            'SEGMENT_DEFAULT': 'data/gl/segment_defaults.csv',
        },
    )
    return GLRepository(store, spark)


def test_get_segment_default_returns_contextual_default(repository):
    result = repository.get_segment_default('DEPT_CD', 'ENTITY_CD', 'USM')

    assert result == SegmentDefault(
        segment_type='DEPT_CD',
        context_type='ENTITY_CD',
        context_value='USM',
        default_value='9999',
    )


def test_get_segment_default_returns_global_default(repository):
    result = repository.get_segment_default('SUB_ACCOUNT', '*', '*')

    assert result == SegmentDefault(
        segment_type='SUB_ACCOUNT',
        context_type='*',
        context_value='*',
        default_value='UNASSIGNED',
    )


def test_get_segment_default_returns_none_for_unknown_combination(repository):
    result = repository.get_segment_default('DEPT_CD', 'ENTITY_CD', 'UNKNOWN')

    assert result is None


def test_get_segment_default_does_not_fall_back_from_contextual_request_to_global_row(
    repository,
):
    # AFFILIATE_CD only has a global (*, *) row configured.
    result = repository.get_segment_default('AFFILIATE_CD', 'ENTITY_CD', 'USM')

    assert result is None


def test_get_segment_default_does_not_fall_back_from_global_request_to_contextual_row(
    repository,
):
    # DEPT_CD only has ENTITY_CD-contextual rows configured.
    result = repository.get_segment_default('DEPT_CD', '*', '*')

    assert result is None


def test_get_segment_default_preserves_numeric_looking_values_as_strings(repository):
    result = repository.get_segment_default('GL_ACCOUNT', 'ENTITY_CD', 'USM')

    assert result.default_value == '999999'
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

    result = repository.get_segment_default('DEPT_CD', 'ENTITY_CD', 'ZZZ')

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


def test_write_posting_persists_all_lineage_and_accounting_fields(posting_repository):
    posting = _posting()

    posting_repository.write_posting(posting)

    results = posting_repository.get_postings(posting.producer_run_id)

    assert len(results) == 1
    result = results[0]
    assert result.gl_posting_id == posting.gl_posting_id
    assert result.workflow_run_id == posting.workflow_run_id
    assert result.producer_run_id == posting.producer_run_id
    assert result.dataclass == posting.dataclass
    assert result.transaction_number == posting.transaction_number
    assert result.line_number == posting.line_number
    assert result.foundry_rule_id == posting.foundry_rule_id
    assert result.posting_id == posting.posting_id
    assert result.posting_stream == posting.posting_stream
    assert result.src_record_id == posting.src_record_id
    assert result.src_app_cd == posting.src_app_cd
    assert result.cr_dr_ind == posting.cr_dr_ind
    assert result.transaction_currency == posting.transaction_currency
    assert result.transaction_amount == posting.transaction_amount
    assert result.accounted_currency == posting.accounted_currency
    assert result.accounted_amount == posting.accounted_amount
    assert result.fx_rate == posting.fx_rate
    assert result.as_of_date == posting.as_of_date
    assert result.business_date == posting.business_date


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

    result = posting_repository.get_postings(posting.producer_run_id)[0]

    assert result.entity_cd == 'USM'
    assert result.dept_cd == '9999'
    assert result.branch_cd == '9999'
    assert result.gl_account == '999999'
    assert result.sub_account == 'UNASSIGNED'
    assert result.affiliate_cd == '999999'
    assert result.product_cd == '999999'
    assert result.book_cd == 'US_DEFAULT'
    assert result.source_cd == 'SRC1'


def test_get_postings_returns_only_the_named_producers_rows(posting_repository):
    # The same business_dt can be processed by multiple GL executions
    # (retries, corrections). get_postings must isolate a single
    # execution's output by producer_run_id, never by business_dt.
    kept = _posting()
    other = _posting(business_date=kept.business_date)

    posting_repository.write_posting(kept)
    posting_repository.write_posting(other)

    results = posting_repository.get_postings(kept.producer_run_id)

    assert len(results) == 1
    assert results[0].producer_run_id == kept.producer_run_id


def test_get_postings_does_not_mix_rows_across_producer_runs_even_with_same_workflow(
    posting_repository,
):
    # Even when both executions share a WORKFLOW_RUN_ID and BUSINESS_DATE,
    # only PRODUCER_RUN_ID may distinguish which execution's rows come back.
    shared_workflow_run_id = uuid4()
    shared_business_date = date(2026, 1, 1)

    g1 = _posting(
        workflow_run_id=shared_workflow_run_id,
        business_date=shared_business_date,
    )
    g2 = _posting(
        workflow_run_id=shared_workflow_run_id,
        business_date=shared_business_date,
    )

    posting_repository.write_posting(g1)
    posting_repository.write_posting(g2)

    g1_results = posting_repository.get_postings(g1.producer_run_id)
    g2_results = posting_repository.get_postings(g2.producer_run_id)

    assert {r.gl_posting_id for r in g1_results} == {g1.gl_posting_id}
    assert {r.gl_posting_id for r in g2_results} == {g2.gl_posting_id}


def test_get_postings_allows_more_than_one_row_for_same_posting_id(posting_repository):
    producer_run_id = uuid4()
    first = _posting(gl_posting_id=uuid4(), posting_id='DUP', producer_run_id=producer_run_id)
    second = _posting(gl_posting_id=uuid4(), posting_id='DUP', producer_run_id=producer_run_id)

    posting_repository.write_posting(first)
    posting_repository.write_posting(second)

    results = posting_repository.get_postings(producer_run_id)

    assert len(results) == 2
    assert {result.posting_id for result in results} == {'DUP'}
    assert {result.gl_posting_id for result in results} == {
        first.gl_posting_id,
        second.gl_posting_id,
    }


def test_write_posting_preserves_decimal_precision(posting_repository):
    posting = _posting(
        transaction_amount=Decimal('12345.123456789012'),
        fx_rate=Decimal('1.123456789012'),
    )

    posting_repository.write_posting(posting)

    result = posting_repository.get_postings(posting.producer_run_id)[0]

    assert result.transaction_amount == Decimal('12345.123456789012')
    assert result.fx_rate == Decimal('1.123456789012')
    assert isinstance(result.fx_rate, Decimal)


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


def test_write_rejection_persists_lineage_and_diagnostics(rejection_repository):
    rejection = _rejection()

    rejection_repository.write_rejection(rejection)

    results = rejection_repository.get_rejections(rejection.producer_run_id)

    assert len(results) == 1
    result = results[0]
    assert result.gl_rejection_id == rejection.gl_rejection_id
    assert result.workflow_run_id == rejection.workflow_run_id
    assert result.producer_run_id == rejection.producer_run_id
    assert result.dataclass == rejection.dataclass
    assert result.transaction_number == rejection.transaction_number
    assert result.line_number == rejection.line_number
    assert result.foundry_rule_id == rejection.foundry_rule_id
    assert result.posting_id == rejection.posting_id
    assert result.posting_stream == rejection.posting_stream
    assert result.src_record_id == rejection.src_record_id
    assert result.src_app_cd == rejection.src_app_cd
    assert result.business_date == rejection.business_date
    assert result.as_of_date == rejection.as_of_date
    assert result.rejection_type == rejection.rejection_type
    assert result.rejection_detail == rejection.rejection_detail


def test_write_rejection_stores_segment_resolution_rejection_type(rejection_repository):
    rejection = _rejection(
        rejection_type='SEGMENT_RESOLUTION',
        rejection_detail='DEPT_CD,BRANCH_CD',
    )

    rejection_repository.write_rejection(rejection)

    result = rejection_repository.get_rejections(rejection.producer_run_id)[0]

    assert result.rejection_type == 'SEGMENT_RESOLUTION'
    assert result.rejection_detail == 'DEPT_CD,BRANCH_CD'


def test_get_rejections_returns_only_the_named_producers_rows(rejection_repository):
    # Same regression scenario as postings: the same business_dt can be
    # processed by multiple GL executions, so business_dt must never be
    # the selector for a specific execution's rejections.
    kept = _rejection()
    other = _rejection(business_date=kept.business_date)

    rejection_repository.write_rejection(kept)
    rejection_repository.write_rejection(other)

    results = rejection_repository.get_rejections(kept.producer_run_id)

    assert len(results) == 1
    assert results[0].producer_run_id == kept.producer_run_id


def test_get_rejections_does_not_mix_rows_across_producer_runs_even_with_same_workflow(
    rejection_repository,
):
    shared_workflow_run_id = uuid4()
    shared_business_date = date(2026, 1, 1)

    g1 = _rejection(
        workflow_run_id=shared_workflow_run_id,
        business_date=shared_business_date,
    )
    g2 = _rejection(
        workflow_run_id=shared_workflow_run_id,
        business_date=shared_business_date,
    )

    rejection_repository.write_rejection(g1)
    rejection_repository.write_rejection(g2)

    g1_results = rejection_repository.get_rejections(g1.producer_run_id)
    g2_results = rejection_repository.get_rejections(g2.producer_run_id)

    assert {r.gl_rejection_id for r in g1_results} == {g1.gl_rejection_id}
    assert {r.gl_rejection_id for r in g2_results} == {g2.gl_rejection_id}


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
        instruction.dept_cd,
        instruction.branch_cd,
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

    results = interface_repository.get_instructions(WORKFLOW_RUN_ID, PRODUCER_RUN_ID)

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

    results = interface_repository.get_instructions(WORKFLOW_RUN_ID, PRODUCER_RUN_ID)

    assert len(results) == 1
    assert results[0].workflow_run_id == WORKFLOW_RUN_ID


def test_get_instructions_excludes_other_producer_runs(interface_repository):
    other_producer_run_id = uuid4()
    _write_instruction_row(interface_repository, _instruction())
    _write_instruction_row(
        interface_repository,
        _instruction(producer_run_id=other_producer_run_id),
    )

    results = interface_repository.get_instructions(WORKFLOW_RUN_ID, PRODUCER_RUN_ID)

    assert len(results) == 1
    assert results[0].producer_run_id == PRODUCER_RUN_ID


def test_get_instructions_maps_all_fields(interface_repository):
    instruction = _instruction()
    _write_instruction_row(interface_repository, instruction)

    result = interface_repository.get_instructions(WORKFLOW_RUN_ID, PRODUCER_RUN_ID)[0]

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

    results = interface_repository.get_instructions(WORKFLOW_RUN_ID, PRODUCER_RUN_ID)

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


def test_delete_postings_removes_only_rows_for_the_named_producer_run(
    posting_and_rejection_repository,
):
    kept_producer_run_id = uuid4()
    deleted_producer_run_id = uuid4()

    posting_and_rejection_repository.write_posting(
        _posting(producer_run_id=kept_producer_run_id)
    )
    posting_and_rejection_repository.write_posting(
        _posting(producer_run_id=deleted_producer_run_id)
    )

    posting_and_rejection_repository.delete_postings(deleted_producer_run_id)

    remaining = posting_and_rejection_repository.get_postings(kept_producer_run_id)
    assert {p.producer_run_id for p in remaining} == {kept_producer_run_id}


def test_delete_rejections_removes_only_rows_for_the_named_producer_run(
    posting_and_rejection_repository,
):
    kept_producer_run_id = uuid4()
    deleted_producer_run_id = uuid4()

    posting_and_rejection_repository.write_rejection(
        _rejection(producer_run_id=kept_producer_run_id)
    )
    posting_and_rejection_repository.write_rejection(
        _rejection(producer_run_id=deleted_producer_run_id)
    )

    posting_and_rejection_repository.delete_rejections(deleted_producer_run_id)

    remaining = posting_and_rejection_repository.get_rejections(kept_producer_run_id)
    assert {r.producer_run_id for r in remaining} == {kept_producer_run_id}
