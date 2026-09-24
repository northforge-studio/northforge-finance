from datetime import date
from decimal import Decimal
from uuid import UUID

from break_analysis.builder import (
    BreakCaseBuilder,
    _PivotCandidate,
    _BreakCaseCandidate,
    _ResolvedCandidate,
)
from break_analysis.models import BreakPartitionKey, BreakTopology, BreakCase
from core.logging import short_id
from gl.models import GLSegmentDefault, GLSegmentDefaults
from registry.models import GLSegmentType

from tests.break_analysis.factories import make_break_record, make_segments
from tests.support.constants import AS_OF_DATE


def _make_partition_key(entity_cd='USM') -> BreakPartitionKey:
    return BreakPartitionKey(
        as_of_date=AS_OF_DATE,
        entity_cd=entity_cd,
        source_cd='SRC1',
        accounted_currency='USD',
    )


def _make_entity_default(
    segment_type: GLSegmentType, entity_cd: str, value: str,
) -> GLSegmentDefault:
    return GLSegmentDefault(
        segment_type=segment_type,
        context_type='ENTITY_CD',
        context_value=entity_cd,
        default_value=value,
    )


def _make_global_default(segment_type: GLSegmentType, value: str) -> GLSegmentDefault:
    return GLSegmentDefault(
        segment_type=segment_type,
        context_type='*',
        context_value='*',
        default_value=value,
    )


def _make_segment_defaults(*entries: GLSegmentDefault) -> GLSegmentDefaults:
    return GLSegmentDefaults(values=entries)


def _make_builder(segment_defaults: GLSegmentDefaults | None = None) -> BreakCaseBuilder:
    return BreakCaseBuilder(segment_defaults if segment_defaults is not None else _make_segment_defaults())


def test_partition_groups_records_with_identical_hard_anchors():
    first = make_break_record()
    second = make_break_record()

    result = _make_builder()._partition([first, second])

    assert len(result) == 1
    [records] = result.values()
    assert set(records) == {first, second}


def test_partition_separates_different_as_of_date():
    same_day = make_break_record()
    other_day = make_break_record(as_of_date=date(2026, 1, 2))

    result = _make_builder()._partition([same_day, other_day])

    assert len(result) == 2


def test_partition_separates_different_entity_cd():
    home_entity = make_break_record()
    other_entity = make_break_record(segments=make_segments(entity_cd='CAM'))

    result = _make_builder()._partition([home_entity, other_entity])

    assert len(result) == 2


def test_partition_separates_different_source_cd():
    home_source = make_break_record()
    other_source = make_break_record(segments=make_segments(source_cd='SRC2'))

    result = _make_builder()._partition([home_source, other_source])

    assert len(result) == 2


def test_partition_separates_different_accounted_currency():
    usd = make_break_record()
    eur = make_break_record(accounted_currency='EUR')

    result = _make_builder()._partition([usd, eur])

    assert len(result) == 2


def test_partition_ignores_differences_in_transformable_segments():
    # BRANCH_CD, DEPT_CD, GL_ACCOUNT, SUB_ACCOUNT, AFFILIATE_CD, PRODUCT_CD
    # and BOOK_CD are transformable segments, not hard anchors, and must
    # not fragment the partition on their own.
    first = make_break_record()
    second = make_break_record(segments=make_segments(
        branch_cd='200',
        dept_cd='4001',
        gl_account='654321',
        sub_account='002',
        affiliate_cd='AFF2',
        product_cd='PRD2',
        book_cd='BK2',
    ))

    result = _make_builder()._partition([first, second])

    assert len(result) == 1
    [records] = result.values()
    assert set(records) == {first, second}


def test_partition_empty_input_returns_empty_dict():
    result = _make_builder()._partition([])

    assert result == {}


def test_partition_builds_one_partition_per_hard_anchor_combination():
    group_a = (make_break_record(), make_break_record())
    group_b = (
        make_break_record(as_of_date=date(2026, 1, 2)),
        make_break_record(as_of_date=date(2026, 1, 2)),
    )
    group_c = (
        make_break_record(segments=make_segments(entity_cd='CAM')),
        make_break_record(segments=make_segments(entity_cd='CAM')),
    )

    result = _make_builder()._partition(group_a + group_b + group_c)

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

def test_resolve_applicable_defaults_uses_entity_specific_default():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)

    result = builder._resolve_applicable_defaults(_make_partition_key(entity_cd='USM'))

    assert result == {GLSegmentType.DEPARTMENT: '9999'}


def test_resolve_applicable_defaults_uses_global_default_without_entity_specific():
    segment_defaults = _make_segment_defaults(
        _make_global_default(GLSegmentType.SUB_ACCOUNT, 'UNASSIGNED'),
    )
    builder = _make_builder(segment_defaults)

    result = builder._resolve_applicable_defaults(_make_partition_key())

    assert result == {GLSegmentType.SUB_ACCOUNT: 'UNASSIGNED'}


def test_resolve_applicable_defaults_excludes_segment_without_default():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)

    result = builder._resolve_applicable_defaults(_make_partition_key())

    assert result == {GLSegmentType.DEPARTMENT: '9999'}
    assert GLSegmentType.BRANCH not in result


# -- _find_pivots ---------------------------------------------------------

def test_find_pivots_relaxes_every_segment_with_a_matching_default():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _make_global_default(GLSegmentType.SUB_ACCOUNT, 'UNASSIGNED'),
    )
    builder = _make_builder(segment_defaults)
    record = make_break_record(segments=make_segments(dept_cd='9999', sub_account='UNASSIGNED'))

    pivots = builder._find_pivots(_make_partition_key(), [record])

    assert len(pivots) == 1
    assert set(pivots[0].relaxed_segments) == {
        GLSegmentType.DEPARTMENT,
        GLSegmentType.SUB_ACCOUNT,
    }


def test_find_pivots_excludes_record_matching_no_defaults():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    # dept_cd stays at its non-default value.
    record = make_break_record()

    pivots = builder._find_pivots(_make_partition_key(), [record])

    assert pivots == ()


def test_find_pivots_ignores_defaults_of_another_entity():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'CAM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    # Value happens to match CAM's configured default, but this record
    # belongs to the USM partition, which has no default of its own.
    record = make_break_record(segments=make_segments(dept_cd='9999'))

    pivots = builder._find_pivots(_make_partition_key(entity_cd='USM'), [record])

    assert pivots == ()


def test_find_pivots_relaxes_only_segments_with_matching_defaults():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _make_global_default(GLSegmentType.SUB_ACCOUNT, 'UNASSIGNED'),
    )
    builder = _make_builder(segment_defaults)
    # sub_account keeps its non-default value, so only DEPARTMENT should relax.
    record = make_break_record(segments=make_segments(dept_cd='9999'))

    pivots = builder._find_pivots(_make_partition_key(), [record])

    assert len(pivots) == 1
    assert pivots[0].relaxed_segments == (GLSegmentType.DEPARTMENT,)


def test_find_pivots_returns_all_pivots_in_partition():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    first = make_break_record(segments=make_segments(dept_cd='9999'))
    second = make_break_record(segments=make_segments(dept_cd='9999'))

    pivots = builder._find_pivots(_make_partition_key(), [first, second])

    assert len(pivots) == 2
    assert {pivot.record for pivot in pivots} == {first, second}


def test_find_pivots_empty_partition_returns_no_pivots():
    builder = _make_builder()

    pivots = builder._find_pivots(_make_partition_key(), [])

    assert pivots == ()


# -- _find_neighborhood ----------------------------------------------------

def test_find_neighborhood_one_relaxed_segment_requires_remaining_to_match():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # Differs only on DEPARTMENT, the relaxed segment; every other
    # transformable segment matches the pivot.
    compatible = make_break_record(segments=make_segments(dept_cd='4000'))

    neighborhood = _make_builder()._find_neighborhood(pivot, [pivot_record, compatible], frozenset())

    assert set(neighborhood) == {pivot_record, compatible}


def test_find_neighborhood_multiple_relaxed_segments_require_all_others_to_match():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999', sub_account='UNASSIGNED'))
    pivot = _PivotCandidate(
        record=pivot_record,
        relaxed_segments=(GLSegmentType.DEPARTMENT, GLSegmentType.SUB_ACCOUNT),
    )
    # Differs only on the two relaxed segments; every non-relaxed
    # transformable segment matches the pivot.
    compatible = make_break_record(segments=make_segments(dept_cd='4000', sub_account='001'))

    neighborhood = _make_builder()._find_neighborhood(pivot, [pivot_record, compatible], frozenset())

    assert set(neighborhood) == {pivot_record, compatible}


def test_find_neighborhood_excludes_record_differing_on_effective_anchor():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # branch_cd is an effective anchor (not relaxed), so this record must
    # be excluded even though DEPARTMENT differs too.
    unrelated = make_break_record(segments=make_segments(dept_cd='9999', branch_cd='200'))

    neighborhood = _make_builder()._find_neighborhood(pivot, [pivot_record, unrelated], frozenset())

    assert neighborhood == (pivot_record,)


def test_find_neighborhood_excludes_other_matching_pivots():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # Matches the pivot's effective anchors, but is itself another pivot,
    # so it must not be absorbed into this pivot's neighborhood.
    other_pivot_record = make_break_record(difference_amount=Decimal('-50.00'))
    pivot_ids = frozenset({
        pivot_record.recon_result_id,
        other_pivot_record.recon_result_id,
    })

    neighborhood = _make_builder()._find_neighborhood(
        pivot,
        [pivot_record, other_pivot_record],
        pivot_ids,
    )

    assert neighborhood == (pivot_record,)


def test_find_neighborhood_includes_current_pivot():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    pivot_ids = frozenset({pivot_record.recon_result_id})

    neighborhood = _make_builder()._find_neighborhood(pivot, [pivot_record], pivot_ids)

    assert neighborhood == (pivot_record,)


def test_find_neighborhood_includes_matching_non_pivot():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # Matches the pivot's effective anchors and is not itself a pivot, so
    # it must remain in the neighborhood.
    compatible = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))
    pivot_ids = frozenset({pivot_record.recon_result_id})

    neighborhood = _make_builder()._find_neighborhood(
        pivot,
        [pivot_record, compatible],
        pivot_ids,
    )

    assert set(neighborhood) == {pivot_record, compatible}


def test_find_neighborhood_excludes_pivot_with_wider_relaxed_segments():
    account_pivot_record = make_break_record(
        segments=make_segments(gl_account='999999'),
        difference_amount=Decimal('50.00'),
    )
    account_pivot = _PivotCandidate(
        record=account_pivot_record,
        relaxed_segments=(GLSegmentType.ACCOUNT,),
    )
    # Would match the ACCOUNT-only pivot's effective anchors (SUB_ACCOUNT
    # included), but is itself a pivot with a wider set of relaxed
    # segments, so it must not be absorbed.
    account_and_sub_account_pivot_record = make_break_record(
        segments=make_segments(gl_account='999999', sub_account='001'),
        difference_amount=Decimal('-50.00'),
    )
    pivot_ids = frozenset({
        account_pivot_record.recon_result_id,
        account_and_sub_account_pivot_record.recon_result_id,
    })

    neighborhood = _make_builder()._find_neighborhood(
        account_pivot,
        [account_pivot_record, account_and_sub_account_pivot_record],
        pivot_ids,
    )

    assert neighborhood == (account_pivot_record,)


# -- _is_closed -------------------------------------------------------------

def test_is_closed_true_for_offsetting_differences():
    first = make_break_record(difference_amount=Decimal('50.00'))
    second = make_break_record(difference_amount=Decimal('-50.00'))

    assert _make_builder()._is_closed([first, second]) is True


def test_is_closed_false_for_nonzero_net_difference():
    first = make_break_record(difference_amount=Decimal('50.00'))
    second = make_break_record(difference_amount=Decimal('-30.00'))

    assert _make_builder()._is_closed([first, second]) is False


def test_is_closed_true_for_empty_records():
    assert _make_builder()._is_closed([]) is True


# -- _build_candidate ---------------------------------------------------------

def test_build_candidate_two_record_neighborhood_yields_one_to_one():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    offsetting = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))

    candidate = _make_builder()._build_candidate(pivot, [pivot_record, offsetting], frozenset())

    assert candidate is not None
    assert candidate.topology == BreakTopology.ONE_TO_ONE
    assert set(candidate.all_records) == {pivot_record, offsetting}


def test_build_candidate_three_or_more_records_yield_many_to_one():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    first = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-20.00'))
    second = make_break_record(segments=make_segments(dept_cd='0001'), difference_amount=Decimal('-30.00'))

    candidate = _make_builder()._build_candidate(pivot, [pivot_record, first, second], frozenset())

    assert candidate is not None
    assert candidate.topology == BreakTopology.MANY_TO_ONE
    assert set(candidate.all_records) == {pivot_record, first, second}


def test_build_candidate_non_closing_neighborhood_yields_no_candidate():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    non_offsetting = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-30.00'))

    candidate = _make_builder()._build_candidate(pivot, [pivot_record, non_offsetting], frozenset())

    assert candidate is None


def test_build_candidate_pivot_only_neighborhood_yields_no_candidate():
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))

    candidate = _make_builder()._build_candidate(pivot, [pivot_record], frozenset())

    assert candidate is None


def test_build_candidate_preserves_pivot_relaxed_segments():
    pivot_record = make_break_record(
        segments=make_segments(dept_cd='9999', sub_account='UNASSIGNED'),
        difference_amount=Decimal('50.00'),
    )
    pivot = _PivotCandidate(
        record=pivot_record,
        relaxed_segments=(GLSegmentType.DEPARTMENT, GLSegmentType.SUB_ACCOUNT),
    )
    offsetting = make_break_record(
        segments=make_segments(dept_cd='4000', sub_account='001'),
        difference_amount=Decimal('-50.00'),
    )

    candidate = _make_builder()._build_candidate(pivot, [pivot_record, offsetting], frozenset())

    assert candidate is not None
    assert candidate.relaxed_segments == (GLSegmentType.DEPARTMENT, GLSegmentType.SUB_ACCOUNT)


# -- _find_candidates -----------------------------------------------------

def test_find_candidates_builds_one_candidate_per_valid_pivot():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    # Two independent branches, each with its own pivot/offsetting pair.
    pivot_a = make_break_record(segments=make_segments(branch_cd='100', dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_a = make_break_record(segments=make_segments(branch_cd='100', dept_cd='4000'), difference_amount=Decimal('-50.00'))
    pivot_b = make_break_record(segments=make_segments(branch_cd='200', dept_cd='9999'), difference_amount=Decimal('30.00'))
    partner_b = make_break_record(segments=make_segments(branch_cd='200', dept_cd='4000'), difference_amount=Decimal('-30.00'))

    candidates = builder._find_candidates(
        _make_partition_key(),
        (pivot_a, partner_a, pivot_b, partner_b),
    )

    assert len(candidates) == 2
    assert {frozenset(c.all_records) for c in candidates} == {
        frozenset({pivot_a, partner_a}),
        frozenset({pivot_b, partner_b}),
    }


def test_find_candidates_builds_separate_neighborhoods_for_identical_anchors():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.ACCOUNT, 'USM', '999999'),
    )
    builder = _make_builder(segment_defaults)
    # Both pivots relax ACCOUNT and are otherwise identical, so they share
    # the same effective-anchor signature and each also matches the
    # other's signature. Without pivot exclusion, pivot_b would be
    # absorbed into pivot_a's neighborhood (and vice versa); each pivot
    # must instead build its own neighborhood from non-pivot records only.
    pivot_a = make_break_record(segments=make_segments(gl_account='999999'), difference_amount=Decimal('50.00'))
    partner_a = make_break_record(segments=make_segments(gl_account='111111'), difference_amount=Decimal('-50.00'))
    pivot_b = make_break_record(segments=make_segments(gl_account='999999'), difference_amount=Decimal('999.00'))

    candidates = builder._find_candidates(
        _make_partition_key(),
        (pivot_a, partner_a, pivot_b),
    )

    # pivot_a closes independently with partner_a; pivot_b's own
    # neighborhood (partner_a, since pivot_a is excluded as another pivot)
    # does not close, so it yields no candidate of its own.
    assert len(candidates) == 1
    assert set(candidates[0].all_records) == {pivot_a, partner_a}


def test_find_candidates_excludes_non_closing_pivot():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    non_offsetting = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-30.00'))

    candidates = builder._find_candidates(_make_partition_key(), (pivot_record, non_offsetting))

    assert candidates == ()


def test_find_candidates_no_pivots_returns_empty_tuple():
    builder = _make_builder()
    record = make_break_record()

    candidates = builder._find_candidates(_make_partition_key(), (record,))

    assert candidates == ()


def test_find_candidates_returns_only_valid_candidates():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    # Branch 100 closes; branch 200 does not.
    closing_pivot = make_break_record(segments=make_segments(branch_cd='100', dept_cd='9999'), difference_amount=Decimal('50.00'))
    closing_partner = make_break_record(segments=make_segments(branch_cd='100', dept_cd='4000'), difference_amount=Decimal('-50.00'))
    open_pivot = make_break_record(segments=make_segments(branch_cd='200', dept_cd='9999'), difference_amount=Decimal('30.00'))
    open_partner = make_break_record(segments=make_segments(branch_cd='200', dept_cd='4000'), difference_amount=Decimal('-10.00'))

    candidates = builder._find_candidates(
        _make_partition_key(),
        (closing_pivot, closing_partner, open_pivot, open_partner),
    )

    assert len(candidates) == 1
    assert set(candidates[0].all_records) == {closing_pivot, closing_partner}


# -- _deduplicate_candidates -----------------------------------------------

def test_deduplicate_candidates_collapses_exact_duplicates():
    pivot = make_break_record()
    investigation = make_break_record()
    candidate = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot,
        investigation_records=(investigation,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    duplicate = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot,
        investigation_records=(investigation,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    result = _make_builder()._deduplicate_candidates([candidate, duplicate])

    assert len(result) == 1
    assert result[0] == candidate


def test_deduplicate_candidates_collapses_same_records_in_different_order():
    pivot = make_break_record()
    first = make_break_record()
    second = make_break_record()
    candidate = _BreakCaseCandidate(
        topology=BreakTopology.MANY_TO_ONE,
        pivot=pivot,
        investigation_records=(first, second),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    reordered = _BreakCaseCandidate(
        topology=BreakTopology.MANY_TO_ONE,
        pivot=pivot,
        investigation_records=(second, first),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    result = _make_builder()._deduplicate_candidates([candidate, reordered])

    assert len(result) == 1


def test_deduplicate_candidates_keeps_different_relaxed_segments_separate():
    pivot = make_break_record()
    investigation = make_break_record()
    department_relaxed = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot,
        investigation_records=(investigation,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    sub_account_relaxed = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot,
        investigation_records=(investigation,),
        relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
    )

    result = _make_builder()._deduplicate_candidates([department_relaxed, sub_account_relaxed])

    assert len(result) == 2


def test_deduplicate_candidates_keeps_different_record_sets_separate():
    first = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=make_break_record(),
        investigation_records=(make_break_record(),),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    second = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=make_break_record(),
        investigation_records=(make_break_record(),),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    result = _make_builder()._deduplicate_candidates([first, second])

    assert len(result) == 2


def test_deduplicate_candidates_empty_returns_empty_tuple():
    result = _make_builder()._deduplicate_candidates([])

    assert result == ()


# -- _resolve_candidates -----------------------------------------------------

def test_resolve_candidates_accepts_single_candidate_unchanged():
    pivot = make_break_record()
    investigation = make_break_record()
    candidate = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot,
        investigation_records=(investigation,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    resolved = _make_builder()._resolve_candidates([candidate])

    assert resolved == (
        _ResolvedCandidate(
            topology=BreakTopology.ONE_TO_ONE,
            pivot=pivot,
            investigation_records=(investigation,),
            relaxed_segments=(GLSegmentType.DEPARTMENT,),
        ),
    )


def test_resolve_candidates_accepts_non_overlapping_candidates_independently():
    pivot_a, first = make_break_record(), make_break_record()
    pivot_b, second = make_break_record(), make_break_record()
    candidate_a = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot_a,
        investigation_records=(first,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    candidate_b = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot_b,
        investigation_records=(second,),
        relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
    )

    resolved = _make_builder()._resolve_candidates([candidate_a, candidate_b])

    assert len(resolved) == 2
    assert set(resolved) == {
        _ResolvedCandidate(
            topology=BreakTopology.ONE_TO_ONE,
            pivot=pivot_a,
            investigation_records=(first,),
            relaxed_segments=(GLSegmentType.DEPARTMENT,),
        ),
        _ResolvedCandidate(
            topology=BreakTopology.ONE_TO_ONE,
            pivot=pivot_b,
            investigation_records=(second,),
            relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
        ),
    }


def test_resolve_candidates_two_overlapping_yield_one_ambiguous_result():
    shared_pivot = make_break_record()
    only_in_a = make_break_record()
    only_in_b = make_break_record()
    candidate_a = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=shared_pivot,
        investigation_records=(only_in_a,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    candidate_b = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=shared_pivot,
        investigation_records=(only_in_b,),
        relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
    )

    resolved = _make_builder()._resolve_candidates([candidate_a, candidate_b])

    assert len(resolved) == 1
    assert resolved[0].topology == BreakTopology.AMBIGUOUS
    assert resolved[0].relaxed_segments is None


def test_resolve_candidates_transitive_overlap_yields_one_ambiguous_result():
    only_in_a = make_break_record()
    shared_ab = make_break_record()
    shared_bc = make_break_record()
    only_in_c = make_break_record()
    # candidate_a and candidate_c share no record directly, but both
    # overlap with candidate_b, so all three must merge transitively.
    candidate_a = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=shared_ab,
        investigation_records=(only_in_a,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    candidate_b = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=shared_ab,
        investigation_records=(shared_bc,),
        relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
    )
    candidate_c = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=shared_bc,
        investigation_records=(only_in_c,),
        relaxed_segments=(GLSegmentType.BRANCH,),
    )

    resolved = _make_builder()._resolve_candidates([candidate_a, candidate_b, candidate_c])

    assert len(resolved) == 1
    assert resolved[0].topology == BreakTopology.AMBIGUOUS
    assert set(resolved[0].all_records) == {only_in_a, shared_ab, shared_bc, only_in_c}


def test_resolve_candidates_ambiguous_result_unions_records_without_duplicates():
    shared_pivot = make_break_record()
    only_in_a = make_break_record()
    only_in_b = make_break_record()
    candidate_a = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=shared_pivot,
        investigation_records=(only_in_a,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    candidate_b = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=shared_pivot,
        investigation_records=(only_in_b,),
        relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
    )

    resolved = _make_builder()._resolve_candidates([candidate_a, candidate_b])

    assert len(resolved) == 1
    assert len(resolved[0].all_records) == 3
    assert set(resolved[0].all_records) == {shared_pivot, only_in_a, only_in_b}


def test_resolve_candidates_empty_returns_empty_tuple():
    resolved = _make_builder()._resolve_candidates([])

    assert resolved == ()


# -- _to_break_cases ----------------------------------------------------------

def test_to_break_cases_resolved_candidate_carries_evidence():
    pivot, investigation = make_break_record(), make_break_record()
    resolved = _ResolvedCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot,
        investigation_records=(investigation,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    [case] = _make_builder()._to_break_cases([resolved])

    assert isinstance(case, BreakCase)
    assert case.topology == BreakTopology.ONE_TO_ONE
    assert case.pivot == pivot
    assert case.investigation_records == (investigation,)
    assert case.evidence is not None
    assert case.evidence.relaxed_segments == (GLSegmentType.DEPARTMENT,)


def test_to_break_cases_ambiguous_candidate_has_no_evidence():
    first, second = make_break_record(), make_break_record()
    resolved = _ResolvedCandidate(
        topology=BreakTopology.AMBIGUOUS,
        pivot=None,
        investigation_records=(first, second),
        relaxed_segments=None,
    )

    [case] = _make_builder()._to_break_cases([resolved])

    assert case.topology == BreakTopology.AMBIGUOUS
    assert case.evidence is None


def test_to_break_cases_assigns_a_case_id_to_each_case():
    first_resolved = _ResolvedCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=make_break_record(),
        investigation_records=(make_break_record(),),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    second_resolved = _ResolvedCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=make_break_record(),
        investigation_records=(make_break_record(),),
        relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
    )

    cases = _make_builder()._to_break_cases([first_resolved, second_resolved])

    assert len(cases) == 2
    for case in cases:
        assert isinstance(case.case_id, UUID)

    assert cases[0].case_id != cases[1].case_id


# -- _classify_leftovers -------------------------------------------------

def test_classify_leftovers_interface_balance_only_yields_interface_only():
    record = make_break_record(
        interface_balance=Decimal('100.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('100.00'),
    )

    [case] = _make_builder()._classify_leftovers([record])

    assert case.topology == BreakTopology.INTERFACE_ONLY
    assert case.investigation_records == (record,)
    assert case.evidence is None


def test_classify_leftovers_gl_balance_only_yields_gl_only():
    record = make_break_record(
        interface_balance=Decimal('0.00'),
        gl_balance=Decimal('100.00'),
        difference_amount=Decimal('-100.00'),
    )

    [case] = _make_builder()._classify_leftovers([record])

    assert case.topology == BreakTopology.GL_ONLY
    assert case.investigation_records == (record,)


def test_classify_leftovers_both_sides_populated_yields_unmatched():
    record = make_break_record(
        interface_balance=Decimal('100.00'),
        gl_balance=Decimal('80.00'),
        difference_amount=Decimal('20.00'),
    )

    [case] = _make_builder()._classify_leftovers([record])

    assert case.topology == BreakTopology.UNMATCHED
    assert case.investigation_records == (record,)


# -- build ------------------------------------------------------------------

def test_build_known_one_to_one_scenario_yields_one_case():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_record = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))

    cases = builder.build([pivot_record, partner_record])

    assert len(cases) == 1
    [case] = cases
    assert case.topology == BreakTopology.ONE_TO_ONE
    assert set(case.all_records) == {pivot_record, partner_record}


def test_build_known_many_to_one_scenario_yields_one_case():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    first = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-20.00'))
    second = make_break_record(segments=make_segments(dept_cd='0001'), difference_amount=Decimal('-30.00'))

    cases = builder.build([pivot_record, first, second])

    assert len(cases) == 1
    [case] = cases
    assert case.topology == BreakTopology.MANY_TO_ONE
    assert set(case.all_records) == {pivot_record, first, second}


def test_build_multiple_independent_cases_in_same_partition_remain_separate():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    pivot_a = make_break_record(segments=make_segments(branch_cd='100', dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_a = make_break_record(segments=make_segments(branch_cd='100', dept_cd='4000'), difference_amount=Decimal('-50.00'))
    pivot_b = make_break_record(segments=make_segments(branch_cd='200', dept_cd='9999'), difference_amount=Decimal('30.00'))
    partner_b = make_break_record(segments=make_segments(branch_cd='200', dept_cd='4000'), difference_amount=Decimal('-30.00'))

    cases = builder.build([pivot_a, partner_a, pivot_b, partner_b])

    assert len(cases) == 2
    assert all(case.topology == BreakTopology.ONE_TO_ONE for case in cases)
    assert {frozenset(case.all_records) for case in cases} == {
        frozenset({pivot_a, partner_a}),
        frozenset({pivot_b, partner_b}),
    }


def test_build_cases_across_different_partitions_remain_separate():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _make_entity_default(GLSegmentType.DEPARTMENT, 'CAM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    pivot_usm = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_usm = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))
    pivot_cam = make_break_record(
        segments=make_segments(entity_cd='CAM', dept_cd='9999'),
        difference_amount=Decimal('30.00'),
    )
    partner_cam = make_break_record(
        segments=make_segments(entity_cd='CAM', dept_cd='4000'),
        difference_amount=Decimal('-30.00'),
    )

    cases = builder.build([pivot_usm, partner_usm, pivot_cam, partner_cam])

    assert len(cases) == 2
    assert {frozenset(case.all_records) for case in cases} == {
        frozenset({pivot_usm, partner_usm}),
        frozenset({pivot_cam, partner_cam}),
    }


def test_build_overlapping_candidates_yield_ambiguous_case():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _make_entity_default(GLSegmentType.SUB_ACCOUNT, 'USM', 'UNASSIGNED'),
    )
    builder = _make_builder(segment_defaults)
    # Each pivot closes independently against the same shared record, so
    # the two candidates overlap and must merge into one AMBIGUOUS case.
    pivot_a = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot_b = make_break_record(segments=make_segments(sub_account='UNASSIGNED'), difference_amount=Decimal('50.00'))
    shared_partner = make_break_record(difference_amount=Decimal('-50.00'))

    cases = builder.build([pivot_a, pivot_b, shared_partner])

    assert len(cases) == 1
    [case] = cases
    assert case.topology == BreakTopology.AMBIGUOUS
    assert case.evidence is None
    assert set(case.all_records) == {pivot_a, pivot_b, shared_partner}


def test_build_classifies_unconsumed_records_as_leftovers():
    builder = _make_builder()
    interface_only = make_break_record(
        interface_balance=Decimal('100.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('100.00'),
    )

    cases = builder.build([interface_only])

    assert len(cases) == 1
    [case] = cases
    assert case.topology == BreakTopology.INTERFACE_ONLY
    assert case.investigation_records == (interface_only,)
    assert case.evidence is None


def test_build_every_input_record_appears_in_exactly_one_case():
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_record = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))
    leftover = make_break_record(
        interface_balance=Decimal('20.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('20.00'),
    )

    cases = builder.build([pivot_record, partner_record, leftover])

    all_case_record_ids = [
        record.recon_result_id
        for case in cases
        for record in case.all_records
    ]

    assert len(all_case_record_ids) == len(set(all_case_record_ids))
    assert set(all_case_record_ids) == {
        pivot_record.recon_result_id,
        partner_record.recon_result_id,
        leftover.recon_result_id,
    }


def test_build_empty_input_returns_empty_tuple():
    cases = _make_builder().build([])

    assert cases == ()


# -- logging ------------------------------------------------------------

def test_build_logs_topology_breakdown_and_duration(caplog):
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _make_builder(segment_defaults)
    pivot_record = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_record = make_break_record(segments=make_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))
    # Distinct branch_cd keeps this outside the pivot/partner neighborhood
    # (effective anchors), so it surfaces as an unconsumed leftover.
    leftover = make_break_record(
        segments=make_segments(branch_cd='999'),
        interface_balance=Decimal('20.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('20.00'),
    )

    with caplog.at_level('INFO', logger='break_analysis.builder'):
        builder.build([pivot_record, partner_record, leftover])

    summary_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'Break cases built' in r.message
    ]
    assert len(summary_records) == 1
    message = summary_records[0].message
    assert 'total=2' in message
    assert 'one_to_one=1' in message
    assert 'interface_only=1' in message
    assert 'duration_ms=' in message


def test_build_logs_ambiguous_case_as_warning(caplog):
    segment_defaults = _make_segment_defaults(
        _make_entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _make_entity_default(GLSegmentType.SUB_ACCOUNT, 'USM', 'UNASSIGNED'),
    )
    builder = _make_builder(segment_defaults)
    pivot_a = make_break_record(segments=make_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot_b = make_break_record(segments=make_segments(sub_account='UNASSIGNED'), difference_amount=Decimal('50.00'))
    shared_partner = make_break_record(difference_amount=Decimal('-50.00'))

    with caplog.at_level('INFO', logger='break_analysis.builder'):
        [case] = builder.build([pivot_a, pivot_b, shared_partner])

    warning_records = [
        r for r in caplog.records
        if r.levelname == 'WARNING' and 'Ambiguous break case' in r.message
    ]
    assert len(warning_records) == 1
    assert f'case_id={short_id(case.case_id)}' in warning_records[0].message
    assert str(case.case_id) not in warning_records[0].message
