from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from registry import SegmentType

from gl.manager import GLManager
from gl.models import GLInstruction, GLPosting, GLSegments, SegmentDefault, SegmentResolution


BUSINESS_DT = date(2026, 1, 1)


class _FakeRepository:
    def __init__(self, results):
        self._results = results
        self.calls = []


    def get_segment_default(self, segment_type, context_type, context_value):
        self.calls.append((segment_type, context_type, context_value))
        return self._results.get((segment_type, context_type, context_value))


class _FakeRegistryClient:
    def __init__(self, valid_segments):
        self._valid_segments = valid_segments
        self.calls = []


    def validate_segment(self, segment, business_dt, segment_cd):
        self.calls.append((segment, business_dt, segment_cd))
        return (segment, business_dt, segment_cd) in self._valid_segments


def _no_registry_calls_expected():
    """A registry stub for get_segment_default tests, which never touch Registry."""
    return _FakeRegistryClient(set())


def test_contextual_default_is_returned_when_configured():
    repository = _FakeRepository({
        ('DEPT_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='DEPT_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default('DEPT_CD', entity_cd='USM')

    assert result == '9999'
    assert repository.calls == [('DEPT_CD', 'ENTITY_CD', 'USM')]


def test_falls_back_to_global_when_contextual_missing():
    repository = _FakeRepository({
        ('SUB_ACCOUNT', '*', '*'): SegmentDefault(
            segment_type='SUB_ACCOUNT',
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default('SUB_ACCOUNT', entity_cd='USM')

    assert result == 'UNASSIGNED'
    assert repository.calls == [
        ('SUB_ACCOUNT', 'ENTITY_CD', 'USM'),
        ('SUB_ACCOUNT', '*', '*'),
    ]


def test_no_entity_cd_only_tries_global_lookup():
    repository = _FakeRepository({
        ('PRODUCT_CD', '*', '*'): SegmentDefault(
            segment_type='PRODUCT_CD',
            context_type='*',
            context_value='*',
            default_value='999999',
        ),
    })
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default('PRODUCT_CD')

    assert result == '999999'
    assert repository.calls == [('PRODUCT_CD', '*', '*')]


def test_returns_none_when_neither_contextual_nor_global_configured():
    repository = _FakeRepository({})
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default('DEPT_CD', entity_cd='ZZZ')

    assert result is None
    assert repository.calls == [
        ('DEPT_CD', 'ENTITY_CD', 'ZZZ'),
        ('DEPT_CD', '*', '*'),
    ]


def test_contextual_default_takes_precedence_over_global():
    repository = _FakeRepository({
        ('BOOK_CD', 'ENTITY_CD', 'CAM'): SegmentDefault(
            segment_type='BOOK_CD',
            context_type='ENTITY_CD',
            context_value='CAM',
            default_value='CA_DEFAULT',
        ),
        ('BOOK_CD', '*', '*'): SegmentDefault(
            segment_type='BOOK_CD',
            context_type='*',
            context_value='*',
            default_value='SHOULD_NOT_BE_USED',
        ),
    })
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default('BOOK_CD', entity_cd='CAM')

    assert result == 'CA_DEFAULT'
    assert repository.calls == [('BOOK_CD', 'ENTITY_CD', 'CAM')]


def test_segment_with_no_configured_defaults_returns_none():
    repository = _FakeRepository({})
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default('ENTITY_CD', entity_cd='USM')

    assert result is None
    assert repository.calls == [
        ('ENTITY_CD', 'ENTITY_CD', 'USM'),
        ('ENTITY_CD', '*', '*'),
    ]


# -- resolve_segment ---------------------------------------------------

def test_resolve_segment_returns_supplied_value_unchanged_when_registry_valid():
    repository = _FakeRepository({})
    registry = _FakeRegistryClient({
        (SegmentType.DEPARTMENT, BUSINESS_DT, '1234'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'DEPT_CD', '1234',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='DEPT_CD',
        supplied_value='1234',
        resolved_value='1234',
        defaulted=False,
    )
    assert registry.calls == [(SegmentType.DEPARTMENT, BUSINESS_DT, '1234')]
    # No default lookup should occur once the supplied value validates.
    assert repository.calls == []


def test_resolve_segment_uses_contextual_default_when_supplied_invalid():
    repository = _FakeRepository({
        ('DEPT_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='DEPT_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    registry = _FakeRegistryClient({
        (SegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
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
    # validate supplied -> resolve default -> validate default
    assert registry.calls == [
        (SegmentType.DEPARTMENT, BUSINESS_DT, 'BOGUS'),
        (SegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
    ]
    assert repository.calls == [('DEPT_CD', 'ENTITY_CD', 'USM')]


def test_resolve_segment_falls_back_to_global_default_when_contextual_absent():
    repository = _FakeRepository({
        ('SUB_ACCOUNT', '*', '*'): SegmentDefault(
            segment_type='SUB_ACCOUNT',
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    registry = _FakeRegistryClient({
        (SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'SUB_ACCOUNT', 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='SUB_ACCOUNT',
        supplied_value='BOGUS',
        resolved_value='UNASSIGNED',
        defaulted=True,
    )
    assert repository.calls == [
        ('SUB_ACCOUNT', 'ENTITY_CD', 'USM'),
        ('SUB_ACCOUNT', '*', '*'),
    ]


def test_resolve_segment_unresolved_when_no_default_configured():
    repository = _FakeRepository({})
    registry = _FakeRegistryClient(set())
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'DEPT_CD', 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='DEPT_CD',
        supplied_value='BOGUS',
        resolved_value=None,
        defaulted=False,
    )


def test_resolve_segment_unresolved_when_configured_default_is_registry_invalid():
    repository = _FakeRepository({
        ('DEPT_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='DEPT_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    # '9999' is configured but not registered as valid in Registry.
    registry = _FakeRegistryClient(set())
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'DEPT_CD', 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='DEPT_CD',
        supplied_value='BOGUS',
        resolved_value=None,
        defaulted=False,
    )
    # No recursive attempt at another default after a failed default.
    assert repository.calls == [('DEPT_CD', 'ENTITY_CD', 'USM')]


def test_resolve_segment_empty_supplied_value_skips_registry_and_uses_default():
    repository = _FakeRepository({
        ('SUB_ACCOUNT', '*', '*'): SegmentDefault(
            segment_type='SUB_ACCOUNT',
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    registry = _FakeRegistryClient({
        (SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'SUB_ACCOUNT', '',
        business_dt=BUSINESS_DT,
    )

    assert result == SegmentResolution(
        segment_type='SUB_ACCOUNT',
        supplied_value='',
        resolved_value='UNASSIGNED',
        defaulted=True,
    )
    # Only the default value was validated; the empty supplied value
    # was never sent to Registry.
    assert registry.calls == [(SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED')]


def test_resolve_segment_none_supplied_value_skips_registry_and_uses_default():
    repository = _FakeRepository({
        ('SUB_ACCOUNT', '*', '*'): SegmentDefault(
            segment_type='SUB_ACCOUNT',
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    registry = _FakeRegistryClient({
        (SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'SUB_ACCOUNT', None,
        business_dt=BUSINESS_DT,
    )

    assert result.resolved_value == 'UNASSIGNED'
    assert result.defaulted is True
    assert registry.calls == [(SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED')]


def test_resolve_segment_invalid_entity_cd_is_naturally_unresolved():
    # ENTITY_CD is Registry-mapped like any other segment, but
    # gl.segment_default has no configured rows for it.
    repository = _FakeRepository({})
    registry = _FakeRegistryClient(set())
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'ENTITY_CD', 'BOGUS',
        business_dt=BUSINESS_DT,
    )

    assert result == SegmentResolution(
        segment_type='ENTITY_CD',
        supplied_value='BOGUS',
        resolved_value=None,
        defaulted=False,
    )
    assert registry.calls == [(SegmentType.ENTITY, BUSINESS_DT, 'BOGUS')]
    assert repository.calls == [
        ('ENTITY_CD', '*', '*'),
    ]


def test_resolve_segment_invalid_source_cd_is_naturally_unresolved():
    repository = _FakeRepository({})
    registry = _FakeRegistryClient(set())
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'SOURCE_CD', 'BOGUS',
        business_dt=BUSINESS_DT,
    )

    assert result == SegmentResolution(
        segment_type='SOURCE_CD',
        supplied_value='BOGUS',
        resolved_value=None,
        defaulted=False,
    )
    assert registry.calls == [(SegmentType.SOURCE, BUSINESS_DT, 'BOGUS')]


def test_resolve_segment_keeps_valid_supplied_value_even_if_it_looks_like_a_default():
    repository = _FakeRepository({
        ('BOOK_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='BOOK_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='US_DEFAULT',
        ),
    })
    registry = _FakeRegistryClient({
        (SegmentType.BOOK, BUSINESS_DT, 'US_DEFAULT'),
    })
    manager = GLManager(repository, registry)

    # Atlas happens to have supplied exactly the configured GL default,
    # but GL must treat it as an ordinary supplied value, not defaulting.
    result = manager.resolve_segment(
        'BOOK_CD', 'US_DEFAULT',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='BOOK_CD',
        supplied_value='US_DEFAULT',
        resolved_value='US_DEFAULT',
        defaulted=False,
    )
    # The default table was never consulted.
    assert repository.calls == []


def test_resolve_segment_preserves_numeric_looking_values_as_strings():
    repository = _FakeRepository({
        ('GL_ACCOUNT', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='GL_ACCOUNT',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='999999',
        ),
    })
    registry = _FakeRegistryClient({
        (SegmentType.ACCOUNT, BUSINESS_DT, '999999'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        'GL_ACCOUNT', '000000',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result.resolved_value == '999999'
    assert isinstance(result.resolved_value, str)
    assert isinstance(result.supplied_value, str)


# -- resolve_segments ---------------------------------------------------

def _valid_segments() -> GLSegments:
    return GLSegments(
        entity_cd='USM',
        dept_cd='4000',
        branch_cd='100',
        gl_account='123456',
        sub_account='001',
        affiliate_cd='AFF1',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
    )


def _valid_registry_entries() -> set:
    segments = _valid_segments()
    return {
        (SegmentType.ENTITY, BUSINESS_DT, segments.entity_cd),
        (SegmentType.DEPARTMENT, BUSINESS_DT, segments.dept_cd),
        (SegmentType.BRANCH, BUSINESS_DT, segments.branch_cd),
        (SegmentType.ACCOUNT, BUSINESS_DT, segments.gl_account),
        (SegmentType.SUB_ACCOUNT, BUSINESS_DT, segments.sub_account),
        (SegmentType.AFFILIATE, BUSINESS_DT, segments.affiliate_cd),
        (SegmentType.PRODUCT, BUSINESS_DT, segments.product_cd),
        (SegmentType.BOOK, BUSINESS_DT, segments.book_cd),
        (SegmentType.SOURCE, BUSINESS_DT, segments.source_cd),
    }


def test_resolve_segments_all_valid_returns_final_set_unchanged():
    repository = _FakeRepository({})
    registry = _FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    result = manager.resolve_segments(_valid_segments(), business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == _valid_segments()
    assert len(result.resolutions) == 9
    assert all(resolution.defaulted is False for resolution in result.resolutions)
    # No default lookups needed once every supplied value validates.
    assert repository.calls == []


def test_resolve_segments_applies_contextual_default_for_invalid_segment():
    repository = _FakeRepository({
        ('DEPT_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='DEPT_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    registry = _FakeRegistryClient(
        _valid_registry_entries() | {(SegmentType.DEPARTMENT, BUSINESS_DT, '9999')}
    )
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), dept_cd='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == replace(_valid_segments(), dept_cd='9999')

    dept_resolution = next(r for r in result.resolutions if r.segment_type == 'DEPT_CD')
    assert dept_resolution.supplied_value == 'BOGUS'
    assert dept_resolution.resolved_value == '9999'
    assert dept_resolution.defaulted is True

    # Resolved entity was passed as contextual input for the rest.
    assert ('DEPT_CD', 'ENTITY_CD', 'USM') in repository.calls


def test_resolve_segments_applies_global_default_for_invalid_segment():
    repository = _FakeRepository({
        ('SUB_ACCOUNT', '*', '*'): SegmentDefault(
            segment_type='SUB_ACCOUNT',
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    registry = _FakeRegistryClient(
        _valid_registry_entries() | {(SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED')}
    )
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), sub_account='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == replace(_valid_segments(), sub_account='UNASSIGNED')


def test_resolve_segments_applies_defaults_to_multiple_invalid_segments():
    repository = _FakeRepository({
        ('DEPT_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='DEPT_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
        ('SUB_ACCOUNT', '*', '*'): SegmentDefault(
            segment_type='SUB_ACCOUNT',
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
        ('PRODUCT_CD', '*', '*'): SegmentDefault(
            segment_type='PRODUCT_CD',
            context_type='*',
            context_value='*',
            default_value='999999',
        ),
    })
    registry = _FakeRegistryClient(
        _valid_registry_entries() | {
            (SegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
            (SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
            (SegmentType.PRODUCT, BUSINESS_DT, '999999'),
        }
    )
    manager = GLManager(repository, registry)

    supplied = replace(
        _valid_segments(),
        dept_cd='BOGUS',
        sub_account='BOGUS',
        product_cd='BOGUS',
    )

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == replace(
        _valid_segments(),
        dept_cd='9999',
        sub_account='UNASSIGNED',
        product_cd='999999',
    )


def test_resolve_segments_invalid_entity_leaves_whole_set_unresolved():
    repository = _FakeRepository({})
    registry = _FakeRegistryClient(_valid_registry_entries() - {
        (SegmentType.ENTITY, BUSINESS_DT, 'USM'),
    })
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), entity_cd='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is False
    assert result.segments is None
    # Remaining contextual resolution is not attempted once entity fails.
    assert len(result.resolutions) == 1
    assert result.resolutions[0].segment_type == 'ENTITY_CD'
    assert result.resolutions[0].supplied_value == 'BOGUS'
    assert result.resolutions[0].resolved_value is None
    assert repository.calls == [('ENTITY_CD', '*', '*')]


def test_resolve_segments_invalid_source_cd_leaves_whole_set_unresolved():
    repository = _FakeRepository({})
    registry = _FakeRegistryClient(_valid_registry_entries() - {
        (SegmentType.SOURCE, BUSINESS_DT, 'SRC1'),
    })
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), source_cd='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is False
    assert result.segments is None
    # Entity resolved fine, so every other segment was still processed.
    assert len(result.resolutions) == 9
    source_resolution = next(r for r in result.resolutions if r.segment_type == 'SOURCE_CD')
    assert source_resolution.resolved_value is None
    assert source_resolution.defaulted is False


def test_resolve_segments_unresolved_when_configured_default_is_registry_invalid():
    repository = _FakeRepository({
        ('BRANCH_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='BRANCH_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='BAD_DEFAULT',
        ),
    })
    # 'BAD_DEFAULT' is configured but never registered as Registry-valid.
    registry = _FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), branch_cd='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is False
    assert result.segments is None
    branch_resolution = next(r for r in result.resolutions if r.segment_type == 'BRANCH_CD')
    assert branch_resolution.resolved_value is None


def test_resolve_segments_empty_value_is_defaulted():
    repository = _FakeRepository({
        ('DEPT_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='DEPT_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    registry = _FakeRegistryClient(
        _valid_registry_entries() | {(SegmentType.DEPARTMENT, BUSINESS_DT, '9999')}
    )
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), dept_cd='')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == replace(_valid_segments(), dept_cd='9999')


# -- validate_instruction -------------------------------------------------

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
        dept_cd='4000',
        branch_cd='100',
        gl_account='123456',
        sub_account='001',
        affiliate_cd='AFF1',
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


def _manager() -> GLManager:
    return GLManager(_FakeRepository({}), _no_registry_calls_expected())


def test_validate_instruction_fully_valid_has_no_errors():
    result = _manager().validate_instruction(_valid_instruction())

    assert result.valid is True
    assert result.errors == ()


def test_validate_instruction_rejects_invalid_cr_dr_ind():
    instruction = replace(_valid_instruction(), cr_dr_ind='XX')

    result = _manager().validate_instruction(instruction)

    assert result.valid is False
    assert 'INVALID_CR_DR_IND' in result.errors


def test_validate_instruction_rejects_missing_lineage_field():
    instruction = replace(_valid_instruction(), posting_id='')

    result = _manager().validate_instruction(instruction)

    assert result.valid is False
    assert 'MISSING_POSTING_ID' in result.errors


def test_validate_instruction_rejects_missing_transaction_currency():
    instruction = replace(_valid_instruction(), transaction_currency='')

    result = _manager().validate_instruction(instruction)

    assert result.valid is False
    assert 'MISSING_TRANSACTION_CURRENCY' in result.errors


def test_validate_instruction_rejects_missing_accounted_currency():
    instruction = replace(_valid_instruction(), accounted_currency='')

    result = _manager().validate_instruction(instruction)

    assert result.valid is False
    assert 'MISSING_ACCOUNTED_CURRENCY' in result.errors


def test_validate_instruction_rejects_missing_amount():
    instruction = replace(_valid_instruction(), transaction_amount=None)

    result = _manager().validate_instruction(instruction)

    assert result.valid is False
    assert 'MISSING_TRANSACTION_AMOUNT' in result.errors


def test_validate_instruction_rejects_missing_fx_rate():
    instruction = replace(_valid_instruction(), fx_rate=None)

    result = _manager().validate_instruction(instruction)

    assert result.valid is False
    assert 'MISSING_FX_RATE' in result.errors


def test_validate_instruction_collects_multiple_errors_together():
    instruction = replace(
        _valid_instruction(),
        cr_dr_ind='XX',
        transaction_currency='',
        fx_rate=None,
    )

    result = _manager().validate_instruction(instruction)

    assert result.valid is False
    assert set(result.errors) == {
        'INVALID_CR_DR_IND',
        'MISSING_TRANSACTION_CURRENCY',
        'MISSING_FX_RATE',
    }


def test_validate_instruction_allows_empty_defaultable_segment():
    instruction = replace(_valid_instruction(), sub_account='')

    result = _manager().validate_instruction(instruction)

    assert result.valid is True
    assert result.errors == ()


def test_validate_instruction_allows_registry_invalid_looking_segment():
    # Structural validation never checks segment values against
    # Registry — that only happens later, in resolve_segment(s).
    instruction = replace(_valid_instruction(), dept_cd='NOT_A_REAL_DEPT')

    result = _manager().validate_instruction(instruction)

    assert result.valid is True
    assert result.errors == ()


def test_to_segments_produces_matching_gl_segments():
    instruction = _valid_instruction()

    assert instruction.to_segments() == GLSegments(
        entity_cd='USM',
        dept_cd='4000',
        branch_cd='100',
        gl_account='123456',
        sub_account='001',
        affiliate_cd='AFF1',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
    )


# -- GLPosting.from_resolution --------------------------------------------

def test_from_resolution_preserves_lineage_and_accounting_fields():
    instruction = _valid_instruction()
    gl_posting_id = uuid4()
    posted_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    posting = GLPosting.from_resolution(
        instruction,
        instruction.to_segments(),
        gl_posting_id=gl_posting_id,
        posted_at=posted_at,
    )

    assert posting.gl_posting_id == gl_posting_id
    assert posting.posted_at == posted_at
    assert posting.workflow_run_id == instruction.workflow_run_id
    assert posting.producer_run_id == instruction.producer_run_id
    assert posting.dataclass == instruction.dataclass
    assert posting.transaction_number == instruction.transaction_number
    assert posting.line_number == instruction.line_number
    assert posting.foundry_rule_id == instruction.foundry_rule_id
    assert posting.posting_id == instruction.posting_id
    assert posting.posting_stream == instruction.posting_stream
    assert posting.src_record_id == instruction.src_record_id
    assert posting.batch_id == instruction.batch_id
    assert posting.src_app_cd == instruction.src_app_cd
    assert posting.cr_dr_ind == instruction.cr_dr_ind
    assert posting.transaction_currency == instruction.transaction_currency
    assert posting.transaction_amount == instruction.transaction_amount
    assert posting.accounted_currency == instruction.accounted_currency
    assert posting.accounted_amount == instruction.accounted_amount
    assert posting.fx_rate == instruction.fx_rate
    assert posting.as_of_date == instruction.as_of_date
    assert posting.business_date == instruction.business_date


def test_from_resolution_uses_resolved_segments_not_instruction_original():
    # Interface supplied an invalid DEPT_CD; resolve_segments would have
    # substituted the GL default ('9999') before this factory ever runs.
    instruction = replace(_valid_instruction(), dept_cd='BOGUS_INVALID')
    resolved_segments = replace(instruction.to_segments(), dept_cd='9999')

    posting = GLPosting.from_resolution(
        instruction,
        resolved_segments,
        gl_posting_id=uuid4(),
        posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    # The resolved value made it through...
    assert posting.dept_cd == '9999'
    # ...and the original Interface-supplied value did not leak in.
    assert posting.dept_cd != instruction.dept_cd
