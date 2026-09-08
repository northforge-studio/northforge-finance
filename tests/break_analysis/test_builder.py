from datetime import date
from decimal import Decimal
from uuid import uuid4

from registry.models import GLSegmentType

from break_analysis.builder import BreakCaseBuilder, _PivotCandidate, _BreakCaseCandidate
from break_analysis.models import BreakPartitionKey, BreakRecord, BreakTopology
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


# -- _find_neighborhood ----------------------------------------------------

def test_one_relaxed_segment_requires_remaining_segments_to_match():
    pivot_record = _record(segments=_segments(dept_cd='9999'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # Differs only on DEPARTMENT, the relaxed segment; every other
    # transformable segment matches the pivot.
    compatible = _record(segments=_segments(dept_cd='4000'))

    neighborhood = _builder()._find_neighborhood(pivot, [pivot_record, compatible])

    assert set(neighborhood) == {pivot_record, compatible}


def test_multiple_relaxed_segments_require_all_other_segments_to_match():
    pivot_record = _record(segments=_segments(dept_cd='9999', sub_account='UNASSIGNED'))
    pivot = _PivotCandidate(
        record=pivot_record,
        relaxed_segments=(GLSegmentType.DEPARTMENT, GLSegmentType.SUB_ACCOUNT),
    )
    # Differs only on the two relaxed segments; every non-relaxed
    # transformable segment matches the pivot.
    compatible = _record(segments=_segments(dept_cd='4000', sub_account='001'))

    neighborhood = _builder()._find_neighborhood(pivot, [pivot_record, compatible])

    assert set(neighborhood) == {pivot_record, compatible}


def test_difference_on_any_effective_anchor_excludes_the_record():
    pivot_record = _record(segments=_segments(dept_cd='9999'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # branch_cd is an effective anchor (not relaxed), so this record must
    # be excluded even though DEPARTMENT differs too.
    unrelated = _record(segments=_segments(dept_cd='9999', branch_cd='200'))

    neighborhood = _builder()._find_neighborhood(pivot, [pivot_record, unrelated])

    assert neighborhood == (pivot_record,)


# -- _is_closed -------------------------------------------------------------

def test_records_with_offsetting_differences_are_closed():
    first = _record(difference_amount=Decimal('50.00'))
    second = _record(difference_amount=Decimal('-50.00'))

    assert _builder()._is_closed([first, second]) is True


def test_records_with_nonzero_net_difference_are_not_closed():
    first = _record(difference_amount=Decimal('50.00'))
    second = _record(difference_amount=Decimal('-30.00'))

    assert _builder()._is_closed([first, second]) is False


def test_empty_records_are_closed():
    assert _builder()._is_closed([]) is True


# -- _build_candidate ---------------------------------------------------------

def test_closed_two_record_neighborhood_yields_one_to_one():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    offsetting = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))

    candidate = _builder()._build_candidate(pivot, [pivot_record, offsetting])

    assert candidate is not None
    assert candidate.topology == BreakTopology.ONE_TO_ONE
    assert set(candidate.records) == {pivot_record, offsetting}


def test_closed_three_or_more_record_neighborhood_yields_many_to_one():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    first = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-20.00'))
    second = _record(segments=_segments(dept_cd='0001'), difference_amount=Decimal('-30.00'))

    candidate = _builder()._build_candidate(pivot, [pivot_record, first, second])

    assert candidate is not None
    assert candidate.topology == BreakTopology.MANY_TO_ONE
    assert set(candidate.records) == {pivot_record, first, second}


def test_non_closing_neighborhood_yields_no_candidate():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    non_offsetting = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-30.00'))

    candidate = _builder()._build_candidate(pivot, [pivot_record, non_offsetting])

    assert candidate is None


def test_neighborhood_containing_only_the_pivot_yields_no_candidate():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))

    candidate = _builder()._build_candidate(pivot, [pivot_record])

    assert candidate is None


def test_candidate_preserves_pivot_relaxed_segments():
    pivot_record = _record(
        segments=_segments(dept_cd='9999', sub_account='UNASSIGNED'),
        difference_amount=Decimal('50.00'),
    )
    pivot = _PivotCandidate(
        record=pivot_record,
        relaxed_segments=(GLSegmentType.DEPARTMENT, GLSegmentType.SUB_ACCOUNT),
    )
    offsetting = _record(
        segments=_segments(dept_cd='4000', sub_account='001'),
        difference_amount=Decimal('-50.00'),
    )

    candidate = _builder()._build_candidate(pivot, [pivot_record, offsetting])

    assert candidate is not None
    assert candidate.relaxed_segments == (GLSegmentType.DEPARTMENT, GLSegmentType.SUB_ACCOUNT)


# -- _find_candidates -----------------------------------------------------

def test_multiple_valid_pivots_each_build_a_candidate():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    # Two independent branches, each with its own pivot/offsetting pair.
    pivot_a = _record(segments=_segments(branch_cd='100', dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_a = _record(segments=_segments(branch_cd='100', dept_cd='4000'), difference_amount=Decimal('-50.00'))
    pivot_b = _record(segments=_segments(branch_cd='200', dept_cd='9999'), difference_amount=Decimal('30.00'))
    partner_b = _record(segments=_segments(branch_cd='200', dept_cd='4000'), difference_amount=Decimal('-30.00'))

    candidates = builder._find_candidates(
        _partition_key(),
        (pivot_a, partner_a, pivot_b, partner_b),
    )

    assert len(candidates) == 2
    assert {frozenset(c.records) for c in candidates} == {
        frozenset({pivot_a, partner_a}),
        frozenset({pivot_b, partner_b}),
    }


def test_non_closing_pivot_is_excluded():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    non_offsetting = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-30.00'))

    candidates = builder._find_candidates(_partition_key(), (pivot_record, non_offsetting))

    assert candidates == ()


def test_no_pivots_returns_empty_tuple():
    builder = _builder()
    record = _record()

    candidates = builder._find_candidates(_partition_key(), (record,))

    assert candidates == ()


def test_mix_of_valid_and_invalid_pivots_returns_only_valid_candidates():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    # Branch 100 closes; branch 200 does not.
    closing_pivot = _record(segments=_segments(branch_cd='100', dept_cd='9999'), difference_amount=Decimal('50.00'))
    closing_partner = _record(segments=_segments(branch_cd='100', dept_cd='4000'), difference_amount=Decimal('-50.00'))
    open_pivot = _record(segments=_segments(branch_cd='200', dept_cd='9999'), difference_amount=Decimal('30.00'))
    open_partner = _record(segments=_segments(branch_cd='200', dept_cd='4000'), difference_amount=Decimal('-10.00'))

    candidates = builder._find_candidates(
        _partition_key(),
        (closing_pivot, closing_partner, open_pivot, open_partner),
    )

    assert len(candidates) == 1
    assert set(candidates[0].records) == {closing_pivot, closing_partner}


# -- _deduplicate_candidates -----------------------------------------------

def test_exact_duplicate_candidates_collapse_to_one():
    first = _record()
    second = _record()
    candidate = _BreakCaseCandidate(
        records=(first, second),
        topology=BreakTopology.ONE_TO_ONE,
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    duplicate = _BreakCaseCandidate(
        records=(first, second),
        topology=BreakTopology.ONE_TO_ONE,
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    result = _builder()._deduplicate_candidates([candidate, duplicate])

    assert len(result) == 1
    assert result[0] == candidate


def test_same_records_in_different_order_are_still_duplicates():
    first = _record()
    second = _record()
    candidate = _BreakCaseCandidate(
        records=(first, second),
        topology=BreakTopology.ONE_TO_ONE,
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    reordered = _BreakCaseCandidate(
        records=(second, first),
        topology=BreakTopology.ONE_TO_ONE,
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    result = _builder()._deduplicate_candidates([candidate, reordered])

    assert len(result) == 1


def test_same_records_with_different_relaxed_segments_remain_separate():
    first = _record()
    second = _record()
    department_relaxed = _BreakCaseCandidate(
        records=(first, second),
        topology=BreakTopology.ONE_TO_ONE,
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    sub_account_relaxed = _BreakCaseCandidate(
        records=(first, second),
        topology=BreakTopology.ONE_TO_ONE,
        relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
    )

    result = _builder()._deduplicate_candidates([department_relaxed, sub_account_relaxed])

    assert len(result) == 2


def test_different_record_sets_remain_separate():
    first = _BreakCaseCandidate(
        records=(_record(), _record()),
        topology=BreakTopology.ONE_TO_ONE,
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    second = _BreakCaseCandidate(
        records=(_record(), _record()),
        topology=BreakTopology.ONE_TO_ONE,
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    result = _builder()._deduplicate_candidates([first, second])

    assert len(result) == 2


def test_empty_candidates_returns_empty_tuple():
    result = _builder()._deduplicate_candidates([])

    assert result == ()
