from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from registry.models import GLSegmentType

from core.runs.models import RunIdentity

from gl.manager import GLManager
from gl.models import (
    GLInstruction,
    GLPosting,
    GLSegments,
    GLSegmentDefault,
    GLSegmentResolution,
)

from tests.support.constants import BUSINESS_DT
from tests.support.fakes import FakeRegistryClient


class _FakeRepository:
    def __init__(self, results, instructions=(), postings_by_workflow=None, rejections_by_workflow=None):
        self._results = results
        self._instructions = instructions
        self._postings_by_workflow = postings_by_workflow or {}
        self._rejections_by_workflow = rejections_by_workflow or {}
        self.calls = []
        self.postings = []
        self.rejections = []
        self.deleted_posting_workflow_run_ids = []
        self.deleted_rejection_workflow_run_ids = []
        self.get_instructions_calls = []
        self.get_postings_calls = []
        self.get_rejections_calls = []


    def get_segment_default(self, segment_type, context_type, context_value):
        self.calls.append((segment_type, context_type, context_value))
        return self._results.get((segment_type, context_type, context_value))


    def write_posting(self, posting):
        self.postings.append(posting)


    def write_rejection(self, rejection):
        self.rejections.append(rejection)


    def get_instructions(self, workflow_run_id):
        self.get_instructions_calls.append(workflow_run_id)
        return self._instructions


    def delete_postings(self, workflow_run_id):
        self.deleted_posting_workflow_run_ids.append(workflow_run_id)


    def delete_rejections(self, workflow_run_id):
        self.deleted_rejection_workflow_run_ids.append(workflow_run_id)


    def get_postings(self, workflow_run_id):
        self.get_postings_calls.append(workflow_run_id)
        return self._postings_by_workflow.get(workflow_run_id, ())


    def get_rejections(self, workflow_run_id):
        self.get_rejections_calls.append(workflow_run_id)
        return self._rejections_by_workflow.get(workflow_run_id, ())


def _no_registry_calls_expected():
    '''A registry stub for get_segment_default tests, which never touch Registry.'''
    return FakeRegistryClient(set())


def test_contextual_default_is_returned_when_configured():
    repository = _FakeRepository({
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.DEPARTMENT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default(GLSegmentType.DEPARTMENT, entity_cd='USM')

    assert result == '9999'
    assert repository.calls == [(GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM')]


def test_falls_back_to_global_when_contextual_missing():
    repository = _FakeRepository({
        (GLSegmentType.SUB_ACCOUNT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.SUB_ACCOUNT,
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default(GLSegmentType.SUB_ACCOUNT, entity_cd='USM')

    assert result == 'UNASSIGNED'
    assert repository.calls == [
        (GLSegmentType.SUB_ACCOUNT, 'ENTITY_CD', 'USM'),
        (GLSegmentType.SUB_ACCOUNT, '*', '*'),
    ]


def test_no_entity_cd_only_tries_global_lookup():
    repository = _FakeRepository({
        (GLSegmentType.PRODUCT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.PRODUCT,
            context_type='*',
            context_value='*',
            default_value='999999',
        ),
    })
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default(GLSegmentType.PRODUCT)

    assert result == '999999'
    assert repository.calls == [(GLSegmentType.PRODUCT, '*', '*')]


def test_returns_none_when_neither_contextual_nor_global_configured():
    repository = _FakeRepository({})
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default(GLSegmentType.DEPARTMENT, entity_cd='ZZZ')

    assert result is None
    assert repository.calls == [
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'ZZZ'),
        (GLSegmentType.DEPARTMENT, '*', '*'),
    ]


def test_contextual_default_takes_precedence_over_global():
    repository = _FakeRepository({
        (GLSegmentType.BOOK, 'ENTITY_CD', 'CAM'): GLSegmentDefault(
            segment_type=GLSegmentType.BOOK,
            context_type='ENTITY_CD',
            context_value='CAM',
            default_value='CA_DEFAULT',
        ),
        (GLSegmentType.BOOK, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.BOOK,
            context_type='*',
            context_value='*',
            default_value='SHOULD_NOT_BE_USED',
        ),
    })
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_segment_default(GLSegmentType.BOOK, entity_cd='CAM')

    assert result == 'CA_DEFAULT'
    assert repository.calls == [(GLSegmentType.BOOK, 'ENTITY_CD', 'CAM')]


# -- resolve_segment ---------------------------------------------------

def test_resolve_segment_returns_supplied_value_unchanged_when_registry_valid():
    repository = _FakeRepository({})
    registry = FakeRegistryClient({
        (GLSegmentType.DEPARTMENT, BUSINESS_DT, '1234'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        GLSegmentType.DEPARTMENT, '1234',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.DEPARTMENT,
        supplied_value='1234',
        resolved_value='1234',
        defaulted=False,
    )
    assert registry.calls == [(GLSegmentType.DEPARTMENT, BUSINESS_DT, '1234')]
    # No default lookup should occur once the supplied value validates.
    assert repository.calls == []


def test_resolve_segment_uses_contextual_default_when_supplied_invalid():
    repository = _FakeRepository({
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.DEPARTMENT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    registry = FakeRegistryClient({
        (GLSegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        GLSegmentType.DEPARTMENT, 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.DEPARTMENT,
        supplied_value='BOGUS',
        resolved_value='9999',
        defaulted=True,
    )
    # validate supplied -> resolve default -> validate default
    assert registry.calls == [
        (GLSegmentType.DEPARTMENT, BUSINESS_DT, 'BOGUS'),
        (GLSegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
    ]
    assert repository.calls == [(GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM')]


def test_resolve_segment_falls_back_to_global_default_when_contextual_absent():
    repository = _FakeRepository({
        (GLSegmentType.SUB_ACCOUNT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.SUB_ACCOUNT,
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    registry = FakeRegistryClient({
        (GLSegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        GLSegmentType.SUB_ACCOUNT, 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.SUB_ACCOUNT,
        supplied_value='BOGUS',
        resolved_value='UNASSIGNED',
        defaulted=True,
    )
    assert repository.calls == [
        (GLSegmentType.SUB_ACCOUNT, 'ENTITY_CD', 'USM'),
        (GLSegmentType.SUB_ACCOUNT, '*', '*'),
    ]


def test_resolve_segment_unresolved_when_no_default_configured():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(set())
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        GLSegmentType.DEPARTMENT, 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.DEPARTMENT,
        supplied_value='BOGUS',
        resolved_value=None,
        defaulted=False,
    )


def test_resolve_segment_unresolved_when_configured_default_is_registry_invalid():
    repository = _FakeRepository({
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.DEPARTMENT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    # '9999' is configured but not registered as valid in Registry.
    registry = FakeRegistryClient(set())
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        GLSegmentType.DEPARTMENT, 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.DEPARTMENT,
        supplied_value='BOGUS',
        resolved_value=None,
        defaulted=False,
    )
    # No recursive attempt at another default after a failed default.
    assert repository.calls == [(GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM')]


def test_resolve_segment_empty_supplied_value_skips_registry_and_uses_default():
    repository = _FakeRepository({
        (GLSegmentType.SUB_ACCOUNT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.SUB_ACCOUNT,
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    registry = FakeRegistryClient({
        (GLSegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        GLSegmentType.SUB_ACCOUNT, '',
        business_dt=BUSINESS_DT,
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.SUB_ACCOUNT,
        supplied_value='',
        resolved_value='UNASSIGNED',
        defaulted=True,
    )
    # Only the default value was validated; the empty supplied value
    # was never sent to Registry.
    assert registry.calls == [(GLSegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED')]


def test_resolve_segment_invalid_entity_cd_is_naturally_unresolved():
    # ENTITY is Registry-mapped like any other segment, but
    # gl.segment_default has no configured rows for it.
    repository = _FakeRepository({})
    registry = FakeRegistryClient(set())
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        GLSegmentType.ENTITY, 'BOGUS',
        business_dt=BUSINESS_DT,
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.ENTITY,
        supplied_value='BOGUS',
        resolved_value=None,
        defaulted=False,
    )
    assert registry.calls == [(GLSegmentType.ENTITY, BUSINESS_DT, 'BOGUS')]
    assert repository.calls == [
        (GLSegmentType.ENTITY, '*', '*'),
    ]


def test_resolve_segment_keeps_valid_supplied_value_even_if_it_looks_like_a_default():
    repository = _FakeRepository({
        (GLSegmentType.BOOK, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.BOOK,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='US_DEFAULT',
        ),
    })
    registry = FakeRegistryClient({
        (GLSegmentType.BOOK, BUSINESS_DT, 'US_DEFAULT'),
    })
    manager = GLManager(repository, registry)

    # Atlas happens to have supplied exactly the configured GL default,
    # but GL must treat it as an ordinary supplied value, not defaulting.
    result = manager.resolve_segment(
        GLSegmentType.BOOK, 'US_DEFAULT',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.BOOK,
        supplied_value='US_DEFAULT',
        resolved_value='US_DEFAULT',
        defaulted=False,
    )
    # The default table was never consulted.
    assert repository.calls == []


def test_resolve_segment_preserves_numeric_looking_values_as_strings():
    repository = _FakeRepository({
        (GLSegmentType.ACCOUNT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.ACCOUNT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='999999',
        ),
    })
    registry = FakeRegistryClient({
        (GLSegmentType.ACCOUNT, BUSINESS_DT, '999999'),
    })
    manager = GLManager(repository, registry)

    result = manager.resolve_segment(
        GLSegmentType.ACCOUNT, '000000',
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
        (GLSegmentType.ENTITY, BUSINESS_DT, segments.entity_cd),
        (GLSegmentType.DEPARTMENT, BUSINESS_DT, segments.dept_cd),
        (GLSegmentType.BRANCH, BUSINESS_DT, segments.branch_cd),
        (GLSegmentType.ACCOUNT, BUSINESS_DT, segments.gl_account),
        (GLSegmentType.SUB_ACCOUNT, BUSINESS_DT, segments.sub_account),
        (GLSegmentType.AFFILIATE, BUSINESS_DT, segments.affiliate_cd),
        (GLSegmentType.PRODUCT, BUSINESS_DT, segments.product_cd),
        (GLSegmentType.BOOK, BUSINESS_DT, segments.book_cd),
        (GLSegmentType.SOURCE, BUSINESS_DT, segments.source_cd),
    }


def test_resolve_segments_all_valid_returns_final_set_unchanged():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
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
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.DEPARTMENT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    registry = FakeRegistryClient(
        _valid_registry_entries() | {(GLSegmentType.DEPARTMENT, BUSINESS_DT, '9999')}
    )
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), dept_cd='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == replace(_valid_segments(), dept_cd='9999')

    dept_resolution = next(
        r for r in result.resolutions if r.segment_type == GLSegmentType.DEPARTMENT
    )
    assert dept_resolution.supplied_value == 'BOGUS'
    assert dept_resolution.resolved_value == '9999'
    assert dept_resolution.defaulted is True

    # Resolved entity was passed as contextual input for the rest.
    assert (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM') in repository.calls


def test_resolve_segments_applies_global_default_for_invalid_segment():
    repository = _FakeRepository({
        (GLSegmentType.SUB_ACCOUNT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.SUB_ACCOUNT,
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
    })
    registry = FakeRegistryClient(
        _valid_registry_entries() | {(GLSegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED')}
    )
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), sub_account='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == replace(_valid_segments(), sub_account='UNASSIGNED')


def test_resolve_segments_applies_defaults_to_multiple_invalid_segments():
    repository = _FakeRepository({
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.DEPARTMENT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
        (GLSegmentType.SUB_ACCOUNT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.SUB_ACCOUNT,
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
        (GLSegmentType.PRODUCT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.PRODUCT,
            context_type='*',
            context_value='*',
            default_value='999999',
        ),
    })
    registry = FakeRegistryClient(
        _valid_registry_entries() | {
            (GLSegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
            (GLSegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
            (GLSegmentType.PRODUCT, BUSINESS_DT, '999999'),
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
    registry = FakeRegistryClient(_valid_registry_entries() - {
        (GLSegmentType.ENTITY, BUSINESS_DT, 'USM'),
    })
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), entity_cd='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is False
    assert result.segments is None
    # Remaining contextual resolution is not attempted once entity fails.
    assert len(result.resolutions) == 1
    assert result.resolutions[0].segment_type == GLSegmentType.ENTITY
    assert result.resolutions[0].supplied_value == 'BOGUS'
    assert result.resolutions[0].resolved_value is None
    assert repository.calls == [(GLSegmentType.ENTITY, '*', '*')]


def test_resolve_segments_invalid_source_cd_leaves_whole_set_unresolved():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries() - {
        (GLSegmentType.SOURCE, BUSINESS_DT, 'SRC1'),
    })
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), source_cd='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is False
    assert result.segments is None
    # Entity resolved fine, so every other segment was still processed.
    assert len(result.resolutions) == 9
    source_resolution = next(
        r for r in result.resolutions if r.segment_type == GLSegmentType.SOURCE
    )
    assert source_resolution.resolved_value is None
    assert source_resolution.defaulted is False


def test_resolve_segments_unresolved_when_configured_default_is_registry_invalid():
    repository = _FakeRepository({
        (GLSegmentType.BRANCH, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.BRANCH,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='BAD_DEFAULT',
        ),
    })
    # 'BAD_DEFAULT' is configured but never registered as Registry-valid.
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    supplied = replace(_valid_segments(), branch_cd='BOGUS')

    result = manager.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is False
    assert result.segments is None
    branch_resolution = next(
        r for r in result.resolutions if r.segment_type == GLSegmentType.BRANCH
    )
    assert branch_resolution.resolved_value is None


def test_resolve_segments_empty_value_is_defaulted():
    repository = _FakeRepository({
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.DEPARTMENT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    registry = FakeRegistryClient(
        _valid_registry_entries() | {(GLSegmentType.DEPARTMENT, BUSINESS_DT, '9999')}
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

def test_from_resolution_stamps_the_supplied_gl_execution_lineage():
    # GL output lineage is the GL execution's own identity, not a copy of
    # the Interface instruction's lineage (see test_manager below for the
    # end-to-end version of this via process_instruction/import_instructions).
    instruction = _valid_instruction()
    gl_posting_id = uuid4()
    posted_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    gl_workflow_run_id = instruction.workflow_run_id
    gl_producer_run_id = uuid4()

    posting = GLPosting.from_resolution(
        instruction,
        instruction.to_segments(),
        gl_posting_id=gl_posting_id,
        posted_at=posted_at,
        workflow_run_id=gl_workflow_run_id,
        producer_run_id=gl_producer_run_id,
    )

    assert posting.gl_posting_id == gl_posting_id
    assert posting.posted_at == posted_at
    assert posting.workflow_run_id == gl_workflow_run_id
    assert posting.producer_run_id == gl_producer_run_id
    assert posting.producer_run_id != instruction.producer_run_id
    assert posting.dataclass == instruction.dataclass
    assert posting.transaction_number == instruction.transaction_number
    assert posting.line_number == instruction.line_number
    assert posting.foundry_rule_id == instruction.foundry_rule_id
    assert posting.posting_id == instruction.posting_id
    assert posting.posting_stream == instruction.posting_stream
    assert posting.src_record_id == instruction.src_record_id
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
        workflow_run_id=instruction.workflow_run_id,
        producer_run_id=uuid4(),
    )

    # The resolved value made it through...
    assert posting.dept_cd == '9999'
    # ...and the original Interface-supplied value did not leak in.
    assert posting.dept_cd != instruction.dept_cd


# -- process_instruction ---------------------------------------------------

def test_process_instruction_without_identity_falls_back_to_instruction_lineage():
    # Direct/standalone use (no orchestrated GL execution) keeps the prior
    # behavior of stamping the instruction's own lineage.
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    instruction = _valid_instruction()

    result = manager.process_instruction(instruction)

    assert result.posting.workflow_run_id == instruction.workflow_run_id
    assert result.posting.producer_run_id == instruction.producer_run_id


def test_process_instruction_with_identity_stamps_gl_execution_lineage():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    instruction = _valid_instruction()
    identity = RunIdentity(workflow_run_id=uuid4(), run_id=uuid4(), parent_run_id=None)

    result = manager.process_instruction(instruction, identity=identity)

    assert result.posting.workflow_run_id == identity.workflow_run_id
    assert result.posting.producer_run_id == identity.run_id
    assert result.posting.producer_run_id != instruction.producer_run_id


def test_process_instruction_valid_posts_successfully():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    instruction = _valid_instruction()

    result = manager.process_instruction(instruction)

    assert result.posted is True
    assert result.rejection is None
    assert result.validation.valid is True
    assert result.segment_resolution.resolved is True
    assert result.posting is not None
    assert result.posting.dept_cd == instruction.dept_cd
    assert repository.postings == [result.posting]
    assert repository.rejections == []


def test_process_instruction_defaulted_segment_posts_resolved_value():
    repository = _FakeRepository({
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.DEPARTMENT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    registry = FakeRegistryClient(
        _valid_registry_entries() | {(GLSegmentType.DEPARTMENT, BUSINESS_DT, '9999')}
    )
    manager = GLManager(repository, registry)
    instruction = replace(_valid_instruction(), dept_cd='BOGUS')

    result = manager.process_instruction(instruction)

    assert result.posted is True
    assert result.posting.dept_cd == '9999'
    # Original Interface-supplied value is untouched.
    assert instruction.dept_cd == 'BOGUS'


def test_process_instruction_structural_failure_rejects_without_posting():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    instruction = replace(_valid_instruction(), cr_dr_ind='XX')

    result = manager.process_instruction(instruction)

    assert result.posted is False
    assert result.posting is None
    assert result.segment_resolution is None
    assert result.rejection is not None
    assert result.rejection.rejection_type == 'STRUCTURAL_VALIDATION'
    assert 'INVALID_CR_DR_IND' in result.rejection.rejection_detail
    assert repository.postings == []
    assert repository.rejections == [result.rejection]
    # Registry is never consulted once structural validation fails.
    assert registry.calls == []


def test_process_instruction_invalid_entity_rejects_via_segment_resolution():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(set())
    manager = GLManager(repository, registry)
    instruction = replace(_valid_instruction(), entity_cd='BOGUS')

    result = manager.process_instruction(instruction)

    assert result.posted is False
    assert result.posting is None
    assert result.rejection.rejection_type == 'SEGMENT_RESOLUTION'
    assert result.rejection.rejection_detail == 'ENTITY_CD'
    assert repository.postings == []


def test_process_instruction_invalid_source_rejects_via_segment_resolution():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(
        _valid_registry_entries() - {(GLSegmentType.SOURCE, BUSINESS_DT, 'SRC1')}
    )
    manager = GLManager(repository, registry)
    instruction = replace(_valid_instruction(), source_cd='BOGUS')

    result = manager.process_instruction(instruction)

    assert result.posted is False
    assert result.rejection.rejection_type == 'SEGMENT_RESOLUTION'
    assert 'SOURCE_CD' in result.rejection.rejection_detail
    assert repository.postings == []


def test_process_instruction_multiple_defaults_produce_one_posting():
    repository = _FakeRepository({
        (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
            segment_type=GLSegmentType.DEPARTMENT,
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
        (GLSegmentType.SUB_ACCOUNT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.SUB_ACCOUNT,
            context_type='*',
            context_value='*',
            default_value='UNASSIGNED',
        ),
        (GLSegmentType.PRODUCT, '*', '*'): GLSegmentDefault(
            segment_type=GLSegmentType.PRODUCT,
            context_type='*',
            context_value='*',
            default_value='999999',
        ),
    })
    registry = FakeRegistryClient(
        _valid_registry_entries() | {
            (GLSegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
            (GLSegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
            (GLSegmentType.PRODUCT, BUSINESS_DT, '999999'),
        }
    )
    manager = GLManager(repository, registry)
    instruction = replace(
        _valid_instruction(),
        dept_cd='BOGUS',
        sub_account='BOGUS',
        product_cd='BOGUS',
    )

    result = manager.process_instruction(instruction)

    assert result.posted is True
    assert result.posting.dept_cd == '9999'
    assert result.posting.sub_account == 'UNASSIGNED'
    assert result.posting.product_cd == '999999'
    assert len(repository.postings) == 1


def test_process_instruction_generates_uuid_and_utc_timestamp_by_default():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    result = manager.process_instruction(_valid_instruction())

    assert isinstance(result.posting.gl_posting_id, UUID)
    assert isinstance(result.posting.posted_at, datetime)
    assert result.posting.posted_at.tzinfo is not None


def test_process_instruction_accepts_injected_deterministic_ids():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    fixed_id = uuid4()
    fixed_time = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

    result = manager.process_instruction(
        _valid_instruction(),
        gl_posting_id=fixed_id,
        posted_at=fixed_time,
    )

    assert result.posting.gl_posting_id == fixed_id
    assert result.posting.posted_at == fixed_time


def test_process_instruction_accepts_injected_deterministic_rejection_ids():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    fixed_id = uuid4()
    fixed_time = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

    result = manager.process_instruction(
        replace(_valid_instruction(), cr_dr_ind='XX'),
        gl_rejection_id=fixed_id,
        rejected_at=fixed_time,
    )

    assert result.rejection.gl_rejection_id == fixed_id
    assert result.rejection.rejected_at == fixed_time


def test_process_instruction_never_writes_both_posting_and_rejection():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    posted_result = manager.process_instruction(_valid_instruction())
    assert posted_result.posted is True
    assert len(repository.postings) == 1
    assert len(repository.rejections) == 0

    rejected_result = manager.process_instruction(
        replace(_valid_instruction(), cr_dr_ind='XX')
    )
    assert rejected_result.posted is False
    assert len(repository.postings) == 1
    assert len(repository.rejections) == 1


# -- import_instructions -----------------------------------------------

def _gl_identity(**overrides) -> RunIdentity:
    defaults = dict(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=None,
    )
    defaults.update(overrides)
    return RunIdentity(**defaults)


def test_import_instructions_all_valid_partition_all_posted():
    valid_1 = _valid_instruction()
    valid_2 = replace(_valid_instruction(), transaction_number='TXN-2')
    repository = _FakeRepository({}, instructions=(valid_1, valid_2))
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    identity = _gl_identity()
    source_producer_run_id = uuid4()

    result = manager.import_instructions(identity, source_producer_run_id)

    assert result.workflow_run_id == identity.workflow_run_id
    assert result.producer_run_id == identity.run_id
    assert result.source_producer_run_id == source_producer_run_id
    assert result.received_count == 2
    assert result.posted_count == 2
    assert result.rejected_count == 0
    assert all(r.posted for r in result.results)
    assert len(repository.postings) == 2


def test_import_instructions_mixed_partition_posts_valid_rejects_invalid():
    valid = _valid_instruction()
    invalid = replace(_valid_instruction(), transaction_number='TXN-2', cr_dr_ind='XX')
    repository = _FakeRepository({}, instructions=(invalid, valid))
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    result = manager.import_instructions(_gl_identity(), uuid4())

    assert result.received_count == 2
    assert result.posted_count == 1
    assert result.rejected_count == 1
    assert result.received_count == result.posted_count + result.rejected_count
    # One rejection does not stop processing of the remaining instruction.
    assert result.results[0].posted is False
    assert result.results[1].posted is True


def test_import_instructions_business_rejections_do_not_fail_the_import():
    # A partial/rejected batch is still a *successful* import at the
    # GLImportResult/GLManager level; only a raised exception signals a
    # technical failure. The orchestrator relies on this to keep
    # GL/IMPORT SUCCEEDED even when rejected_count > 0.
    invalid = replace(_valid_instruction(), cr_dr_ind='XX')
    repository = _FakeRepository({}, instructions=(invalid,))
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    result = manager.import_instructions(_gl_identity(), uuid4())

    assert result.received_count == 1
    assert result.posted_count == 0
    assert result.rejected_count == 1


def test_import_instructions_empty_partition_returns_zero_counts():
    repository = _FakeRepository({}, instructions=())
    registry = FakeRegistryClient(set())
    manager = GLManager(repository, registry)

    result = manager.import_instructions(_gl_identity(), uuid4())

    assert result.received_count == 0
    assert result.posted_count == 0
    assert result.rejected_count == 0
    assert result.results == ()


def test_import_instructions_results_retained_in_deterministic_order():
    first = replace(_valid_instruction(), transaction_number='TXN-1')
    second = replace(_valid_instruction(), transaction_number='TXN-2')
    third = replace(_valid_instruction(), transaction_number='TXN-3')
    repository = _FakeRepository({}, instructions=(first, second, third))
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    result = manager.import_instructions(_gl_identity(), uuid4())

    assert [r.posting.transaction_number for r in result.results] == [
        'TXN-1', 'TXN-2', 'TXN-3',
    ]


def test_import_instructions_defaulted_segment_appears_in_posting():
    repository = _FakeRepository(
        {
            (GLSegmentType.DEPARTMENT, 'ENTITY_CD', 'USM'): GLSegmentDefault(
                segment_type=GLSegmentType.DEPARTMENT,
                context_type='ENTITY_CD',
                context_value='USM',
                default_value='9999',
            ),
        },
        instructions=(replace(_valid_instruction(), dept_cd='BOGUS'),),
    )
    registry = FakeRegistryClient(
        _valid_registry_entries() | {(GLSegmentType.DEPARTMENT, BUSINESS_DT, '9999')}
    )
    manager = GLManager(repository, registry)

    result = manager.import_instructions(_gl_identity(), uuid4())

    assert result.results[0].posting.dept_cd == '9999'
    assert repository.postings[0].dept_cd == '9999'


def test_import_instructions_does_not_prevent_duplicate_posting_id():
    same_posting_id = replace(_valid_instruction(), transaction_number='TXN-1')
    repository = _FakeRepository(
        {}, instructions=(same_posting_id, same_posting_id)
    )
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)

    result = manager.import_instructions(_gl_identity(), uuid4())

    assert result.posted_count == 2
    assert len(repository.postings) == 2
    assert {p.posting_id for p in repository.postings} == {same_posting_id.posting_id}
    # No app-level uniqueness enforcement on posting_id.
    assert repository.postings[0].gl_posting_id != repository.postings[1].gl_posting_id


def test_import_instructions_stamps_gl_execution_lineage_not_interface_lineage():
    # This is the key GL output-lineage fix: postings/rejections must carry
    # the GL execution's own identity (identity.workflow_run_id / run_id),
    # not the Interface producer_run_id the instruction arrived with.
    interface_producer_run_id = uuid4()
    valid = replace(
        _valid_instruction(),
        producer_run_id=interface_producer_run_id,
    )
    invalid = replace(
        _valid_instruction(),
        transaction_number='TXN-2',
        cr_dr_ind='XX',
        producer_run_id=interface_producer_run_id,
    )
    repository = _FakeRepository({}, instructions=(valid, invalid))
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    identity = _gl_identity()

    manager.import_instructions(identity, interface_producer_run_id)

    [posting] = repository.postings
    assert posting.workflow_run_id == identity.workflow_run_id
    assert posting.producer_run_id == identity.run_id
    assert posting.producer_run_id != interface_producer_run_id

    [rejection] = repository.rejections
    assert rejection.workflow_run_id == identity.workflow_run_id
    assert rejection.producer_run_id == identity.run_id
    assert rejection.producer_run_id != interface_producer_run_id


def test_import_instructions_reads_by_workflow_run_id_not_source_producer_run_id():
    repository = _FakeRepository({}, instructions=(_valid_instruction(),))
    registry = FakeRegistryClient(_valid_registry_entries())
    manager = GLManager(repository, registry)
    identity = _gl_identity()
    source_producer_run_id = uuid4()

    manager.import_instructions(identity, source_producer_run_id)

    # V1 invariant: one Interface producer execution per workflow, so
    # Interface rows are selected by WORKFLOW_RUN_ID alone, not by
    # business_dt, a "latest batch" lookup, or source_producer_run_id
    # (which is retained only as lineage on the returned GLImportResult).
    assert repository.get_instructions_calls == [identity.workflow_run_id]


# -- rollback_execution ------------------------------------------------

def test_rollback_execution_deletes_only_postings_and_rejections_for_the_workflow():
    repository = _FakeRepository({})
    registry = FakeRegistryClient(set())
    manager = GLManager(repository, registry)
    identity = _gl_identity()

    manager.rollback_execution(identity)

    assert repository.deleted_posting_workflow_run_ids == [identity.workflow_run_id]
    assert repository.deleted_rejection_workflow_run_ids == [identity.workflow_run_id]


# -- get_postings / get_rejections --------------------------------------

def test_get_postings_delegates_to_repository_by_workflow_run_id():
    workflow_run_id = uuid4()
    expected = (object(),)
    repository = _FakeRepository({}, postings_by_workflow={workflow_run_id: expected})
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_postings(workflow_run_id)

    assert result == expected
    assert repository.get_postings_calls == [workflow_run_id]


def test_get_rejections_delegates_to_repository_by_workflow_run_id():
    workflow_run_id = uuid4()
    expected = (object(),)
    repository = _FakeRepository({}, rejections_by_workflow={workflow_run_id: expected})
    manager = GLManager(repository, _no_registry_calls_expected())

    result = manager.get_rejections(workflow_run_id)

    assert result == expected
    assert repository.get_rejections_calls == [workflow_run_id]
