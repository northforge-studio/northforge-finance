import pytest

from gl import GLClient


@pytest.fixture(scope='module')
def gl(spark):
    return GLClient.from_csv(
        spark=spark,
        segment_default_path='data/gl/segment_defaults.csv',
    )


def test_get_segment_default_returns_contextual_default(gl):
    assert gl.get_segment_default('DEPT_CD', entity_cd='USM') == '9999'


def test_get_segment_default_falls_back_to_global(gl):
    assert gl.get_segment_default('SUB_ACCOUNT', entity_cd='USM') == 'UNASSIGNED'


def test_get_segment_default_without_entity_cd_uses_global_only(gl):
    assert gl.get_segment_default('PRODUCT_CD') == '999999'


def test_get_segment_default_returns_none_for_non_defaultable_segments(gl):
    assert gl.get_segment_default('ENTITY_CD', entity_cd='USM') is None
    assert gl.get_segment_default('SOURCE_CD', entity_cd='USM') is None
