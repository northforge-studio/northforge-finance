from datetime import date

import pytest

from registry import SegmentType

from gl import GLClient, SegmentResolution


BUSINESS_DT = date(2026, 1, 1)


class _FakeRegistryClient:
    """Duck-types RegistryClient.validate_segment for delegation tests."""

    def __init__(self, valid_segments):
        self._valid_segments = valid_segments


    def validate_segment(self, segment, business_dt, segment_cd):
        return (segment, business_dt, segment_cd) in self._valid_segments


@pytest.fixture(scope='module')
def registry():
    return _FakeRegistryClient({
        (SegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
        (SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
    })


@pytest.fixture(scope='module')
def gl(spark, registry):
    return GLClient.from_csv(
        spark=spark,
        segment_default_path='data/gl/segment_defaults.csv',
        registry=registry,
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


def test_resolve_segment_delegates_to_manager_for_invalid_supplied_value(gl):
    result = gl.resolve_segment(
        'DEPT_CD', 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='DEPT_CD',
        supplied_value='BOGUS',
        resolved_value='9999',
        defaulted=True,
    )


def test_resolve_segment_delegates_to_manager_for_valid_supplied_value(gl):
    result = gl.resolve_segment(
        'DEPT_CD', '9999',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='DEPT_CD',
        supplied_value='9999',
        resolved_value='9999',
        defaulted=False,
    )
