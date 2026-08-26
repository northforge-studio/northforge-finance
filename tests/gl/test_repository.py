import pytest

from core.store import CsvStore

from gl.models import SegmentDefault
from gl.repository import GLRepository


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            'SEGMENT_DEFAULT': 'data/gl/segment_defaults.csv',
        },
    )
    return GLRepository(store)


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
    repository = GLRepository(store)

    result = repository.get_segment_default('DEPT_CD', 'ENTITY_CD', 'ZZZ')

    assert result.default_value == '0099'
    assert isinstance(result.default_value, str)
