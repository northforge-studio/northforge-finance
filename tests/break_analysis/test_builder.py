from datetime import date
from decimal import Decimal
from uuid import uuid4

from registry.models import GLSegmentType

from break_analysis.builder import BreakCaseBuilder
from break_analysis.models import BreakPartitionKey, BreakRecord
from gl.models import GLSegments, GLSegmentDefault, GLSegmentDefaults


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


def _partition_key(entity_cd='USM') -> BreakPartitionKey:
    return BreakPartitionKey(
        as_of_date=AS_OF_DATE,
        entity_cd=entity_cd,
        source_cd='SRC1',
        accounted_currency='USD',
    )


def _entity_default(segment_type: GLSegmentType, entity_cd: str, value: str) -> GLSegmentDefault:
    return GLSegmentDefault(
        segment_type=segment_type,
        context_type='ENTITY_CD',
        context_value=entity_cd,
        default_value=value,
    )


def _global_default(segment_type: GLSegmentType, value: str) -> GLSegmentDefault:
    return GLSegmentDefault(
        segment_type=segment_type,
        context_type='GLOBAL',
        context_value='*',
        default_value=value,
    )


def _segment_defaults(*entries: GLSegmentDefault) -> GLSegmentDefaults:
    return GLSegmentDefaults(values=entries)


def _builder(segment_defaults: GLSegmentDefaults | None = None) -> BreakCaseBuilder:
    return BreakCaseBuilder(segment_defaults if segment_defaults is not None else _segment_defaults())


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


# -- _resolve_applicable_defaults ---------------------------------------

def test_entity_specific_default_is_resolved_for_the_partition():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)

    result = builder._resolve_applicable_defaults(_partition_key(entity_cd='USM'))

    assert result == {GLSegmentType.DEPARTMENT: '9999'}


def test_global_default_is_used_when_no_entity_specific_default_exists():
    segment_defaults = _segment_defaults(
        _global_default(GLSegmentType.SUB_ACCOUNT, 'UNASSIGNED'),
    )
    builder = _builder(segment_defaults)

    result = builder._resolve_applicable_defaults(_partition_key())

    assert result == {GLSegmentType.SUB_ACCOUNT: 'UNASSIGNED'}


def test_segment_with_no_configured_default_is_excluded_from_applicable_defaults():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)

    result = builder._resolve_applicable_defaults(_partition_key())

    assert result == {GLSegmentType.DEPARTMENT: '9999'}
    assert GLSegmentType.BRANCH not in result


# -- _find_pivots ---------------------------------------------------------

def test_record_matching_one_applicable_default_becomes_a_pivot():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    record = _record(segments=_segments(dept_cd='9999'))

    pivots = builder._find_pivots(_partition_key(), [record])

    assert len(pivots) == 1
    assert pivots[0].record == record
    assert pivots[0].relaxed_segments == (GLSegmentType.DEPARTMENT,)


def test_record_matching_multiple_applicable_defaults_has_all_corresponding_relaxed_segments():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _global_default(GLSegmentType.SUB_ACCOUNT, 'UNASSIGNED'),
    )
    builder = _builder(segment_defaults)
    record = _record(segments=_segments(dept_cd='9999', sub_account='UNASSIGNED'))

    pivots = builder._find_pivots(_partition_key(), [record])

    assert len(pivots) == 1
    assert set(pivots[0].relaxed_segments) == {
        GLSegmentType.DEPARTMENT,
        GLSegmentType.SUB_ACCOUNT,
    }


def test_record_matching_no_applicable_defaults_is_not_a_pivot():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    # dept_cd stays at its non-default value.
    record = _record()

    pivots = builder._find_pivots(_partition_key(), [record])

    assert pivots == ()


def test_default_configured_for_another_entity_does_not_make_a_record_a_pivot():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'CAM', '9999'),
    )
    builder = _builder(segment_defaults)
    # Value happens to match CAM's configured default, but this record
    # belongs to the USM partition, which has no default of its own.
    record = _record(segments=_segments(dept_cd='9999'))

    pivots = builder._find_pivots(_partition_key(entity_cd='USM'), [record])

    assert pivots == ()


def test_matching_one_default_does_not_relax_unrelated_transformable_segments():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _global_default(GLSegmentType.SUB_ACCOUNT, 'UNASSIGNED'),
    )
    builder = _builder(segment_defaults)
    # sub_account keeps its non-default value, so only DEPARTMENT should relax.
    record = _record(segments=_segments(dept_cd='9999'))

    pivots = builder._find_pivots(_partition_key(), [record])

    assert len(pivots) == 1
    assert pivots[0].relaxed_segments == (GLSegmentType.DEPARTMENT,)


def test_multiple_pivot_records_in_the_same_partition_are_all_returned():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    first = _record(segments=_segments(dept_cd='9999'))
    second = _record(segments=_segments(dept_cd='9999'))

    pivots = builder._find_pivots(_partition_key(), [first, second])

    assert len(pivots) == 2
    assert {pivot.record for pivot in pivots} == {first, second}


def test_empty_partition_records_return_no_pivots():
    builder = _builder()

    pivots = builder._find_pivots(_partition_key(), [])

    assert pivots == ()
