from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from core.store import CsvStore

from gl.models import GLPosting, SegmentDefault
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
        batch_id=1,
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

    results = posting_repository.get_postings(date(2026, 1, 1), 1)

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
    assert result.batch_id == posting.batch_id
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

    result = posting_repository.get_postings(date(2026, 1, 1), 1)[0]

    assert result.entity_cd == 'USM'
    assert result.dept_cd == '9999'
    assert result.branch_cd == '9999'
    assert result.gl_account == '999999'
    assert result.sub_account == 'UNASSIGNED'
    assert result.affiliate_cd == '999999'
    assert result.product_cd == '999999'
    assert result.book_cd == 'US_DEFAULT'
    assert result.source_cd == 'SRC1'


def test_get_postings_excludes_different_batch_id(posting_repository):
    posting_repository.write_posting(_posting(batch_id=1))
    posting_repository.write_posting(_posting(batch_id=2))

    results = posting_repository.get_postings(date(2026, 1, 1), 1)

    assert len(results) == 1
    assert results[0].batch_id == 1


def test_get_postings_excludes_different_business_date(posting_repository):
    posting_repository.write_posting(_posting(business_date=date(2026, 1, 1)))
    posting_repository.write_posting(_posting(business_date=date(2026, 1, 2)))

    results = posting_repository.get_postings(date(2026, 1, 1), 1)

    assert len(results) == 1
    assert results[0].business_date == date(2026, 1, 1)


def test_get_postings_allows_more_than_one_row_for_same_posting_id(posting_repository):
    first = _posting(gl_posting_id=uuid4(), posting_id='DUP')
    second = _posting(gl_posting_id=uuid4(), posting_id='DUP')

    posting_repository.write_posting(first)
    posting_repository.write_posting(second)

    results = posting_repository.get_postings(date(2026, 1, 1), 1)

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

    result = posting_repository.get_postings(date(2026, 1, 1), 1)[0]

    assert result.transaction_amount == Decimal('12345.123456789012')
    assert result.fx_rate == Decimal('1.123456789012')
    assert isinstance(result.fx_rate, Decimal)
