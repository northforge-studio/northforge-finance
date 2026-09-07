from datetime import date
from decimal import Decimal
from uuid import uuid4

from break_analysis.builder import BreakCaseBuilder
from break_analysis.models import BreakPartitionKey, BreakRecord
from gl.models import GLSegments


AS_OF_DATE = date(2026, 1, 1)


def _segments(**overrides) -> GLSegments:
    defaults = dict(
        entity_cd='USM',
        branch_cd='100',
        dept_cd='4000',
        gl_account='123456',
        sub_account='001',
        affiliate_cd='AFF1',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
    )
    defaults.update(overrides)
    return GLSegments(**defaults)


def _record(**overrides) -> BreakRecord:
    defaults = dict(
        recon_result_id=uuid4(),
        workflow_run_id=uuid4(),
        as_of_date=AS_OF_DATE,
        segments=_segments(),
        accounted_currency='USD',
        interface_balance=Decimal('100.00'),
        gl_balance=Decimal('100.00'),
        difference_amount=Decimal('0.00'),
    )
    defaults.update(overrides)
    return BreakRecord(**defaults)


def _builder() -> BreakCaseBuilder:
    return BreakCaseBuilder()


def test_records_with_identical_hard_anchors_share_a_partition():
    first = _record()
    second = _record()

    result = _builder()._partition([first, second])

    assert len(result) == 1
    [records] = result.values()
    assert set(records) == {first, second}


def test_different_as_of_date_creates_separate_partition():
    same_day = _record()
    other_day = _record(as_of_date=date(2026, 1, 2))

    result = _builder()._partition([same_day, other_day])

    assert len(result) == 2


def test_different_entity_cd_creates_separate_partition():
    home_entity = _record()
    other_entity = _record(segments=_segments(entity_cd='CAM'))

    result = _builder()._partition([home_entity, other_entity])

    assert len(result) == 2


def test_different_source_cd_creates_separate_partition():
    home_source = _record()
    other_source = _record(segments=_segments(source_cd='SRC2'))

    result = _builder()._partition([home_source, other_source])

    assert len(result) == 2


def test_different_accounted_currency_creates_separate_partition():
    usd = _record()
    eur = _record(accounted_currency='EUR')

    result = _builder()._partition([usd, eur])

    assert len(result) == 2


def test_differences_in_transformable_segments_do_not_create_separate_partitions():
    # BRANCH_CD, DEPT_CD, GL_ACCOUNT, SUB_ACCOUNT, AFFILIATE_CD, PRODUCT_CD
    # and BOOK_CD are transformable segments, not hard anchors, and must
    # not fragment the partition on their own.
    first = _record()
    second = _record(segments=_segments(
        branch_cd='200',
        dept_cd='4001',
        gl_account='654321',
        sub_account='002',
        affiliate_cd='AFF2',
        product_cd='PRD2',
        book_cd='BK2',
    ))

    result = _builder()._partition([first, second])

    assert len(result) == 1
    [records] = result.values()
    assert set(records) == {first, second}


def test_empty_input_returns_empty_dict():
    result = _builder()._partition([])

    assert result == {}


def test_multiple_independent_hard_anchor_combinations_produce_expected_partitions():
    group_a = (_record(), _record())
    group_b = (
        _record(as_of_date=date(2026, 1, 2)),
        _record(as_of_date=date(2026, 1, 2)),
    )
    group_c = (
        _record(segments=_segments(entity_cd='CAM')),
        _record(segments=_segments(entity_cd='CAM')),
    )

    result = _builder()._partition(group_a + group_b + group_c)

    assert len(result) == 3
    assert {len(records) for records in result.values()} == {2}

    expected_keys = {
        BreakPartitionKey(
            as_of_date=AS_OF_DATE,
            entity_cd='USM',
            source_cd='SRC1',
            accounted_currency='USD',
        ),
        BreakPartitionKey(
            as_of_date=date(2026, 1, 2),
            entity_cd='USM',
            source_cd='SRC1',
            accounted_currency='USD',
        ),
        BreakPartitionKey(
            as_of_date=AS_OF_DATE,
            entity_cd='CAM',
            source_cd='SRC1',
            accounted_currency='USD',
        ),
    }
    assert set(result.keys()) == expected_keys
