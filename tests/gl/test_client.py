from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from registry import SegmentType

from gl import GLClient, GLInstruction, GLSegments, SegmentResolution


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
        (SegmentType.ENTITY, BUSINESS_DT, 'USM'),
        (SegmentType.BRANCH, BUSINESS_DT, '100'),
        (SegmentType.ACCOUNT, BUSINESS_DT, '123456'),
        (SegmentType.AFFILIATE, BUSINESS_DT, '999999'),
        (SegmentType.PRODUCT, BUSINESS_DT, 'PRD1'),
        (SegmentType.BOOK, BUSINESS_DT, 'BK1'),
        (SegmentType.SOURCE, BUSINESS_DT, 'SRC1'),
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


def _valid_segments() -> GLSegments:
    return GLSegments(
        entity_cd='USM',
        dept_cd='9999',
        branch_cd='100',
        gl_account='123456',
        sub_account='UNASSIGNED',
        affiliate_cd='999999',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
    )


def test_resolve_segments_delegates_to_manager_when_all_supplied_valid(gl):
    result = gl.resolve_segments(_valid_segments(), business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == _valid_segments()
    assert len(result.resolutions) == 9


def test_resolve_segments_delegates_to_manager_for_invalid_defaultable_segment(gl):
    supplied = replace(_valid_segments(), dept_cd='BOGUS')

    result = gl.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == _valid_segments()

    dept_resolution = next(r for r in result.resolutions if r.segment_type == 'DEPT_CD')
    assert dept_resolution.supplied_value == 'BOGUS'
    assert dept_resolution.resolved_value == '9999'
    assert dept_resolution.defaulted is True


def _valid_instruction() -> GLInstruction:
    return GLInstruction(
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
        as_of_date=date(2026, 1, 1),
        business_date=date(2026, 1, 1),
    )


def test_validate_instruction_delegates_to_manager_for_valid_instruction(gl):
    result = gl.validate_instruction(_valid_instruction())

    assert result.valid is True
    assert result.errors == ()


def test_validate_instruction_delegates_to_manager_for_invalid_instruction(gl):
    instruction = replace(_valid_instruction(), cr_dr_ind='XX')

    result = gl.validate_instruction(instruction)

    assert result.valid is False
    assert 'INVALID_CR_DR_IND' in result.errors
