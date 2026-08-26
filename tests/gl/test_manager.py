from datetime import date

from registry import SegmentType

from gl.manager import GLManager
from gl.models import SegmentDefault, SegmentResolution


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
