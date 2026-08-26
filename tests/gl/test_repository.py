import pytest

from core.db import PostgresConfig, PostgresExecutor
from gl import GLRepository, SegmentDefault


@pytest.fixture(scope='module')
def executor():
    return PostgresExecutor(PostgresConfig.from_env())


@pytest.fixture(scope='module')
def repository():
    return GLRepository()


@pytest.fixture
def segment_defaults(executor):
    rows = [
        ('TEST_SEGMENT_TYPE', 'ENTITY_CD', 'ZZTEST', 'A1'),
        ('TEST_SEGMENT_TYPE', '*', '*', 'GLOBAL1'),
        ('TEST_SEGMENT_TYPE_NUMERIC', 'ENTITY_CD', '0099', '999999'),
    ]

    for segment_type, context_type, context_value, default_value in rows:
        executor.execute(
            '''
            INSERT INTO gl.segments_default (
                segment_type, context_type, context_value, default_value
            ) VALUES (
                :segment_type, :context_type, :context_value, :default_value
            )
            ''',
            {
                'segment_type': segment_type,
                'context_type': context_type,
                'context_value': context_value,
                'default_value': default_value,
            },
        )

    yield

    executor.execute(
        "DELETE FROM gl.segments_default WHERE segment_type LIKE 'TEST\\_%' ESCAPE '\\'"
    )


def test_get_segment_default_returns_contextual_default(repository, segment_defaults):
    result = repository.get_segment_default(
        'TEST_SEGMENT_TYPE', 'ENTITY_CD', 'ZZTEST',
    )

    assert result == SegmentDefault(
        segment_type='TEST_SEGMENT_TYPE',
        context_type='ENTITY_CD',
        context_value='ZZTEST',
        default_value='A1',
    )


def test_get_segment_default_returns_global_default(repository, segment_defaults):
    result = repository.get_segment_default(
        'TEST_SEGMENT_TYPE', '*', '*',
    )

    assert result == SegmentDefault(
        segment_type='TEST_SEGMENT_TYPE',
        context_type='*',
        context_value='*',
        default_value='GLOBAL1',
    )


def test_get_segment_default_returns_none_for_unknown_combination(
    repository, segment_defaults,
):
    result = repository.get_segment_default(
        'TEST_SEGMENT_TYPE', 'ENTITY_CD', 'UNKNOWN',
    )

    assert result is None


def test_get_segment_default_contextual_lookup_does_not_return_global_row(
    repository, segment_defaults,
):
    result = repository.get_segment_default(
        'TEST_SEGMENT_TYPE', 'ENTITY_CD', 'NOT_CONFIGURED',
    )

    assert result is None


def test_get_segment_default_preserves_numeric_looking_values_as_strings(
    repository, segment_defaults,
):
    result = repository.get_segment_default(
        'TEST_SEGMENT_TYPE_NUMERIC', 'ENTITY_CD', '0099',
    )

    assert result.context_value == '0099'
    assert result.default_value == '999999'
    assert isinstance(result.context_value, str)
    assert isinstance(result.default_value, str)
