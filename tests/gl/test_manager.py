from gl.manager import GLManager
from gl.models import SegmentDefault


class _FakeRepository:
    def __init__(self, results):
        self._results = results
        self.calls = []


    def get_segment_default(self, segment_type, context_type, context_value):
        self.calls.append((segment_type, context_type, context_value))
        return self._results.get((segment_type, context_type, context_value))


def test_contextual_default_is_returned_when_configured():
    repository = _FakeRepository({
        ('DEPT_CD', 'ENTITY_CD', 'USM'): SegmentDefault(
            segment_type='DEPT_CD',
            context_type='ENTITY_CD',
            context_value='USM',
            default_value='9999',
        ),
    })
    manager = GLManager(repository)

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
    manager = GLManager(repository)

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
    manager = GLManager(repository)

    result = manager.get_segment_default('PRODUCT_CD')

    assert result == '999999'
    assert repository.calls == [('PRODUCT_CD', '*', '*')]


def test_returns_none_when_neither_contextual_nor_global_configured():
    repository = _FakeRepository({})
    manager = GLManager(repository)

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
    manager = GLManager(repository)

    result = manager.get_segment_default('BOOK_CD', entity_cd='CAM')

    assert result == 'CA_DEFAULT'
    assert repository.calls == [('BOOK_CD', 'ENTITY_CD', 'CAM')]


def test_segment_with_no_configured_defaults_returns_none():
    repository = _FakeRepository({})
    manager = GLManager(repository)

    result = manager.get_segment_default('ENTITY_CD', entity_cd='USM')

    assert result is None
    assert repository.calls == [
        ('ENTITY_CD', 'ENTITY_CD', 'USM'),
        ('ENTITY_CD', '*', '*'),
    ]
