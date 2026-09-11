from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from registry.models import GLSegmentType

from break_analysis.builder import (
    BreakCaseBuilder,
    _PivotCandidate,
    _BreakCaseCandidate,
    _ResolvedCandidate,
)
from break_analysis.models import BreakPartitionKey, BreakRecord, BreakTopology, BreakCase
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
        context_type='*',
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

    neighborhood = _builder()._find_neighborhood(pivot, [pivot_record, compatible], frozenset())

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

    neighborhood = _builder()._find_neighborhood(pivot, [pivot_record, compatible], frozenset())

    assert set(neighborhood) == {pivot_record, compatible}


def test_difference_on_any_effective_anchor_excludes_the_record():
    pivot_record = _record(segments=_segments(dept_cd='9999'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # branch_cd is an effective anchor (not relaxed), so this record must
    # be excluded even though DEPARTMENT differs too.
    unrelated = _record(segments=_segments(dept_cd='9999', branch_cd='200'))

    neighborhood = _builder()._find_neighborhood(pivot, [pivot_record, unrelated], frozenset())

    assert neighborhood == (pivot_record,)


def test_another_pivot_matching_effective_anchors_is_excluded_from_neighborhood():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # Matches the pivot's effective anchors, but is itself another pivot,
    # so it must not be absorbed into this pivot's neighborhood.
    other_pivot_record = _record(difference_amount=Decimal('-50.00'))
    pivot_ids = frozenset({
        pivot_record.recon_result_id,
        other_pivot_record.recon_result_id,
    })

    neighborhood = _builder()._find_neighborhood(
        pivot,
        [pivot_record, other_pivot_record],
        pivot_ids,
    )

    assert neighborhood == (pivot_record,)


def test_current_pivot_record_remains_included_in_its_own_neighborhood():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    pivot_ids = frozenset({pivot_record.recon_result_id})

    neighborhood = _builder()._find_neighborhood(pivot, [pivot_record], pivot_ids)

    assert neighborhood == (pivot_record,)


def test_non_pivot_matching_effective_anchors_remains_included():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    # Matches the pivot's effective anchors and is not itself a pivot, so
    # it must remain in the neighborhood.
    compatible = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))
    pivot_ids = frozenset({pivot_record.recon_result_id})

    neighborhood = _builder()._find_neighborhood(
        pivot,
        [pivot_record, compatible],
        pivot_ids,
    )

    assert set(neighborhood) == {pivot_record, compatible}


def test_pivot_with_narrower_relaxed_segments_cannot_absorb_pivot_with_wider_relaxed_segments():
    account_pivot_record = _record(
        segments=_segments(gl_account='999999'),
        difference_amount=Decimal('50.00'),
    )
    account_pivot = _PivotCandidate(
        record=account_pivot_record,
        relaxed_segments=(GLSegmentType.ACCOUNT,),
    )
    # Would match the ACCOUNT-only pivot's effective anchors (SUB_ACCOUNT
    # included), but is itself a pivot with a wider set of relaxed
    # segments, so it must not be absorbed.
    account_and_sub_account_pivot_record = _record(
        segments=_segments(gl_account='999999', sub_account='001'),
        difference_amount=Decimal('-50.00'),
    )
    pivot_ids = frozenset({
        account_pivot_record.recon_result_id,
        account_and_sub_account_pivot_record.recon_result_id,
    })

    neighborhood = _builder()._find_neighborhood(
        account_pivot,
        [account_pivot_record, account_and_sub_account_pivot_record],
        pivot_ids,
    )

    assert neighborhood == (account_pivot_record,)


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

    candidate = _builder()._build_candidate(pivot, [pivot_record, offsetting], frozenset())

    assert candidate is not None
    assert candidate.topology == BreakTopology.ONE_TO_ONE
    assert set(candidate.all_records) == {pivot_record, offsetting}


def test_closed_three_or_more_record_neighborhood_yields_many_to_one():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    first = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-20.00'))
    second = _record(segments=_segments(dept_cd='0001'), difference_amount=Decimal('-30.00'))

    candidate = _builder()._build_candidate(pivot, [pivot_record, first, second], frozenset())

    assert candidate is not None
    assert candidate.topology == BreakTopology.MANY_TO_ONE
    assert set(candidate.all_records) == {pivot_record, first, second}


def test_non_closing_neighborhood_yields_no_candidate():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))
    non_offsetting = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-30.00'))

    candidate = _builder()._build_candidate(pivot, [pivot_record, non_offsetting], frozenset())

    assert candidate is None


def test_neighborhood_containing_only_the_pivot_yields_no_candidate():
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot = _PivotCandidate(record=pivot_record, relaxed_segments=(GLSegmentType.DEPARTMENT,))

    candidate = _builder()._build_candidate(pivot, [pivot_record], frozenset())

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

    candidate = _builder()._build_candidate(pivot, [pivot_record, offsetting], frozenset())

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
    assert {frozenset(c.all_records) for c in candidates} == {
        frozenset({pivot_a, partner_a}),
        frozenset({pivot_b, partner_b}),
    }


def test_multiple_pivots_with_identical_anchors_independently_build_their_own_neighborhoods():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.ACCOUNT, 'USM', '999999'),
    )
    builder = _builder(segment_defaults)
    # Both pivots relax ACCOUNT and are otherwise identical, so they share
    # the same effective-anchor signature and each also matches the
    # other's signature. Without pivot exclusion, pivot_b would be
    # absorbed into pivot_a's neighborhood (and vice versa); each pivot
    # must instead build its own neighborhood from non-pivot records only.
    pivot_a = _record(segments=_segments(gl_account='999999'), difference_amount=Decimal('50.00'))
    partner_a = _record(segments=_segments(gl_account='111111'), difference_amount=Decimal('-50.00'))
    pivot_b = _record(segments=_segments(gl_account='999999'), difference_amount=Decimal('999.00'))

    candidates = builder._find_candidates(
        _partition_key(),
        (pivot_a, partner_a, pivot_b),
    )

    # pivot_a closes independently with partner_a; pivot_b's own
    # neighborhood (partner_a, since pivot_a is excluded as another pivot)
    # does not close, so it yields no candidate of its own.
    assert len(candidates) == 1
    assert set(candidates[0].all_records) == {pivot_a, partner_a}


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
    assert set(candidates[0].all_records) == {closing_pivot, closing_partner}


# -- _deduplicate_candidates -----------------------------------------------

def test_exact_duplicate_candidates_collapse_to_one():
    pivot = _record()
    investigation = _record()
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

    result = _builder()._deduplicate_candidates([candidate, duplicate])

    assert len(result) == 1
    assert result[0] == candidate


def test_same_investigation_records_in_different_order_are_still_duplicates():
    pivot = _record()
    first = _record()
    second = _record()
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

    result = _builder()._deduplicate_candidates([candidate, reordered])

    assert len(result) == 1


def test_same_records_with_different_relaxed_segments_remain_separate():
    pivot = _record()
    investigation = _record()
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

    result = _builder()._deduplicate_candidates([department_relaxed, sub_account_relaxed])

    assert len(result) == 2


def test_different_record_sets_remain_separate():
    first = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=_record(),
        investigation_records=(_record(),),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    second = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=_record(),
        investigation_records=(_record(),),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    result = _builder()._deduplicate_candidates([first, second])

    assert len(result) == 2


def test_empty_candidates_returns_empty_tuple():
    result = _builder()._deduplicate_candidates([])

    assert result == ()


# -- _resolve_candidates -----------------------------------------------------

def test_single_candidate_is_accepted_unchanged():
    pivot = _record()
    investigation = _record()
    candidate = _BreakCaseCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot,
        investigation_records=(investigation,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    resolved = _builder()._resolve_candidates([candidate])

    assert resolved == (
        _ResolvedCandidate(
            topology=BreakTopology.ONE_TO_ONE,
            pivot=pivot,
            investigation_records=(investigation,),
            relaxed_segments=(GLSegmentType.DEPARTMENT,),
        ),
    )


def test_multiple_non_overlapping_candidates_are_accepted_independently():
    pivot_a, first = _record(), _record()
    pivot_b, second = _record(), _record()
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

    resolved = _builder()._resolve_candidates([candidate_a, candidate_b])

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


def test_two_overlapping_candidates_yield_one_ambiguous_result():
    shared_pivot = _record()
    only_in_a = _record()
    only_in_b = _record()
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

    resolved = _builder()._resolve_candidates([candidate_a, candidate_b])

    assert len(resolved) == 1
    assert resolved[0].topology == BreakTopology.AMBIGUOUS
    assert resolved[0].relaxed_segments is None


def test_transitively_overlapping_candidates_yield_one_ambiguous_result():
    only_in_a = _record()
    shared_ab = _record()
    shared_bc = _record()
    only_in_c = _record()
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

    resolved = _builder()._resolve_candidates([candidate_a, candidate_b, candidate_c])

    assert len(resolved) == 1
    assert resolved[0].topology == BreakTopology.AMBIGUOUS
    assert set(resolved[0].all_records) == {only_in_a, shared_ab, shared_bc, only_in_c}


def test_ambiguous_result_contains_union_of_records_without_duplicates():
    shared_pivot = _record()
    only_in_a = _record()
    only_in_b = _record()
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

    resolved = _builder()._resolve_candidates([candidate_a, candidate_b])

    assert len(resolved) == 1
    assert len(resolved[0].all_records) == 3
    assert set(resolved[0].all_records) == {shared_pivot, only_in_a, only_in_b}


def test_empty_candidates_returns_empty_tuple_for_resolve():
    resolved = _builder()._resolve_candidates([])

    assert resolved == ()


# -- _to_break_cases ----------------------------------------------------------

def test_resolved_normal_candidate_becomes_break_case_with_evidence():
    pivot, investigation = _record(), _record()
    resolved = _ResolvedCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=pivot,
        investigation_records=(investigation,),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )

    [case] = _builder()._to_break_cases([resolved])

    assert isinstance(case, BreakCase)
    assert case.topology == BreakTopology.ONE_TO_ONE
    assert case.pivot == pivot
    assert case.investigation_records == (investigation,)
    assert case.evidence is not None
    assert case.evidence.relaxed_segments == (GLSegmentType.DEPARTMENT,)


def test_ambiguous_candidate_becomes_break_case_with_no_evidence():
    first, second = _record(), _record()
    resolved = _ResolvedCandidate(
        topology=BreakTopology.AMBIGUOUS,
        pivot=None,
        investigation_records=(first, second),
        relaxed_segments=None,
    )

    [case] = _builder()._to_break_cases([resolved])

    assert case.topology == BreakTopology.AMBIGUOUS
    assert case.evidence is None


def test_each_case_gets_a_case_id():
    first_resolved = _ResolvedCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=_record(),
        investigation_records=(_record(),),
        relaxed_segments=(GLSegmentType.DEPARTMENT,),
    )
    second_resolved = _ResolvedCandidate(
        topology=BreakTopology.ONE_TO_ONE,
        pivot=_record(),
        investigation_records=(_record(),),
        relaxed_segments=(GLSegmentType.SUB_ACCOUNT,),
    )

    cases = _builder()._to_break_cases([first_resolved, second_resolved])

    assert len(cases) == 2
    for case in cases:
        assert isinstance(case.case_id, UUID)

    assert cases[0].case_id != cases[1].case_id


# -- _classify_leftovers -------------------------------------------------

def test_classify_leftovers_interface_balance_only_yields_interface_only():
    record = _record(
        interface_balance=Decimal('100.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('100.00'),
    )

    [case] = _builder()._classify_leftovers([record])

    assert case.topology == BreakTopology.INTERFACE_ONLY
    assert case.investigation_records == (record,)
    assert case.evidence is None


def test_classify_leftovers_gl_balance_only_yields_gl_only():
    record = _record(
        interface_balance=Decimal('0.00'),
        gl_balance=Decimal('100.00'),
        difference_amount=Decimal('-100.00'),
    )

    [case] = _builder()._classify_leftovers([record])

    assert case.topology == BreakTopology.GL_ONLY
    assert case.investigation_records == (record,)


def test_classify_leftovers_both_sides_populated_yields_unmatched():
    record = _record(
        interface_balance=Decimal('100.00'),
        gl_balance=Decimal('80.00'),
        difference_amount=Decimal('20.00'),
    )

    [case] = _builder()._classify_leftovers([record])

    assert case.topology == BreakTopology.UNMATCHED
    assert case.investigation_records == (record,)


# -- build ------------------------------------------------------------------

def test_build_known_one_to_one_scenario_yields_one_case():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_record = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))

    cases = builder.build([pivot_record, partner_record])

    assert len(cases) == 1
    [case] = cases
    assert case.topology == BreakTopology.ONE_TO_ONE
    assert set(case.all_records) == {pivot_record, partner_record}


def test_build_known_many_to_one_scenario_yields_one_case():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    first = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-20.00'))
    second = _record(segments=_segments(dept_cd='0001'), difference_amount=Decimal('-30.00'))

    cases = builder.build([pivot_record, first, second])

    assert len(cases) == 1
    [case] = cases
    assert case.topology == BreakTopology.MANY_TO_ONE
    assert set(case.all_records) == {pivot_record, first, second}


def test_build_multiple_independent_cases_in_same_partition_remain_separate():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    pivot_a = _record(segments=_segments(branch_cd='100', dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_a = _record(segments=_segments(branch_cd='100', dept_cd='4000'), difference_amount=Decimal('-50.00'))
    pivot_b = _record(segments=_segments(branch_cd='200', dept_cd='9999'), difference_amount=Decimal('30.00'))
    partner_b = _record(segments=_segments(branch_cd='200', dept_cd='4000'), difference_amount=Decimal('-30.00'))

    cases = builder.build([pivot_a, partner_a, pivot_b, partner_b])

    assert len(cases) == 2
    assert all(case.topology == BreakTopology.ONE_TO_ONE for case in cases)
    assert {frozenset(case.all_records) for case in cases} == {
        frozenset({pivot_a, partner_a}),
        frozenset({pivot_b, partner_b}),
    }


def test_build_cases_across_different_partitions_remain_separate():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _entity_default(GLSegmentType.DEPARTMENT, 'CAM', '9999'),
    )
    builder = _builder(segment_defaults)
    pivot_usm = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_usm = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))
    pivot_cam = _record(
        segments=_segments(entity_cd='CAM', dept_cd='9999'),
        difference_amount=Decimal('30.00'),
    )
    partner_cam = _record(
        segments=_segments(entity_cd='CAM', dept_cd='4000'),
        difference_amount=Decimal('-30.00'),
    )

    cases = builder.build([pivot_usm, partner_usm, pivot_cam, partner_cam])

    assert len(cases) == 2
    assert {frozenset(case.all_records) for case in cases} == {
        frozenset({pivot_usm, partner_usm}),
        frozenset({pivot_cam, partner_cam}),
    }


def test_build_overlapping_candidates_yield_ambiguous_case():
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _entity_default(GLSegmentType.SUB_ACCOUNT, 'USM', 'UNASSIGNED'),
    )
    builder = _builder(segment_defaults)
    # Each pivot closes independently against the same shared record, so
    # the two candidates overlap and must merge into one AMBIGUOUS case.
    pivot_a = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot_b = _record(segments=_segments(sub_account='UNASSIGNED'), difference_amount=Decimal('50.00'))
    shared_partner = _record(difference_amount=Decimal('-50.00'))

    cases = builder.build([pivot_a, pivot_b, shared_partner])

    assert len(cases) == 1
    [case] = cases
    assert case.topology == BreakTopology.AMBIGUOUS
    assert case.evidence is None
    assert set(case.all_records) == {pivot_a, pivot_b, shared_partner}


def test_build_classifies_unconsumed_records_as_leftovers():
    builder = _builder()
    interface_only = _record(
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
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_record = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))
    leftover = _record(
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
    cases = _builder().build([])

    assert cases == ()


# -- logging ------------------------------------------------------------

def test_build_logs_topology_breakdown_and_duration(caplog):
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
    )
    builder = _builder(segment_defaults)
    pivot_record = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    partner_record = _record(segments=_segments(dept_cd='4000'), difference_amount=Decimal('-50.00'))
    # Distinct branch_cd keeps this outside the pivot/partner neighborhood
    # (effective anchors), so it surfaces as an unconsumed leftover.
    leftover = _record(
        segments=_segments(branch_cd='999'),
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
    segment_defaults = _segment_defaults(
        _entity_default(GLSegmentType.DEPARTMENT, 'USM', '9999'),
        _entity_default(GLSegmentType.SUB_ACCOUNT, 'USM', 'UNASSIGNED'),
    )
    builder = _builder(segment_defaults)
    pivot_a = _record(segments=_segments(dept_cd='9999'), difference_amount=Decimal('50.00'))
    pivot_b = _record(segments=_segments(sub_account='UNASSIGNED'), difference_amount=Decimal('50.00'))
    shared_partner = _record(difference_amount=Decimal('-50.00'))

    with caplog.at_level('INFO', logger='break_analysis.builder'):
        [case] = builder.build([pivot_a, pivot_b, shared_partner])

    warning_records = [
        r for r in caplog.records
        if r.levelname == 'WARNING' and 'Ambiguous break case' in r.message
    ]
    assert len(warning_records) == 1
    assert str(case.case_id) in warning_records[0].message
