import pytest

from atlas.manager import MappingManager
from atlas.models import MappingCandidateType
from atlas.repository import AtlasRepository

from tests.support.fakes import FakeStore


_MAPPING_NAME = 'TEST_MAPPING'

_META_COLUMNS = [
    'MAPPING_NAME',
    'MAPPING_DATA_NAME',
    'METADATA_FIELD_NAME',
    'LOGICAL_FIELD_NAME',
    'FIELD_TYPE',
    'LOOKUP_TYPE',
    'SRC_FIELD_NAME',
    'DATATYPE',
    'UI_FIELD_ORDER',
]

_META_ROWS = [
    (_MAPPING_NAME, 'TEST_DATA', 'INPUT_COL1', 'FIELD_A', 'INPUT', 'VALUE', 'FIELD_A', 'STRING', 1),
    (_MAPPING_NAME, 'TEST_DATA', 'INPUT_COL2', 'FIELD_B', 'INPUT', 'VALUE', 'FIELD_B', 'STRING', 2),
    (_MAPPING_NAME, 'TEST_DATA', 'OUTPUT_COL1', 'OUTPUT_VAL', 'OUTPUT', 'VALUE', None, 'STRING', 3),
    (_MAPPING_NAME, 'TEST_DATA', 'WEIGHTAGE', 'WEIGHTAGE', 'LOGICAL', 'VALUE', None, 'STRING', 4),
]

_DATA_COLUMNS = [
    'MAPPING_NAME',
    'INPUT_COL1',
    'INPUT_COL2',
    'OUTPUT_COL1',
    'WEIGHTAGE',
    'STATUS',
]


def _manager(spark, data_rows: list[tuple]) -> MappingManager:
    meta_df = spark.createDataFrame(_META_ROWS, _META_COLUMNS)
    data_df = spark.createDataFrame(data_rows, _DATA_COLUMNS)

    store = FakeStore({
        'MAPPING_META': meta_df,
        'MAPPING_DATA': data_df,
    })

    return MappingManager(AtlasRepository(store))


def test_explain_resolution_specific_candidate_has_no_wildcard_fields(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'OUT1', '1', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
    )

    assert len(evidence.candidates) == 1
    candidate = evidence.candidates[0]
    assert candidate.candidate_type == MappingCandidateType.SPECIFIC
    assert candidate.wildcard_fields == ()
    assert evidence.resolved is True
    assert evidence.mapping_output == {'OUTPUT_VAL': 'OUT1'}


def test_explain_resolution_reports_wildcarded_field(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', '*', 'OUT2', '1', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'ANYTHING'},
    )

    assert len(evidence.candidates) == 1
    candidate = evidence.candidates[0]
    assert candidate.candidate_type == MappingCandidateType.WILDCARD
    assert candidate.wildcard_fields == ('FIELD_B',)


def test_explain_resolution_reports_every_wildcard_field(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, '*', '*', 'OUT3', '1', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
    )

    assert len(evidence.candidates) == 1
    candidate = evidence.candidates[0]
    assert candidate.candidate_type == MappingCandidateType.WILDCARD
    assert candidate.wildcard_fields == ('FIELD_A', 'FIELD_B')


def test_explain_resolution_ranks_active_candidates_by_weightage(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'SPECIFIC_OUT', '9', 'A'),
        (_MAPPING_NAME, 'US', '*', 'WILDCARD_OUT', '1', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
    )

    assert len(evidence.candidates) == 2
    assert evidence.resolved is True
    assert evidence.mapping_output == {'OUTPUT_VAL': 'SPECIFIC_OUT'}


def test_explain_resolution_resolves_through_wildcard_when_specific_inactive(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'SPECIFIC_OUT', '9', 'I'),
        (_MAPPING_NAME, 'US', '*', 'WILDCARD_OUT', '1', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
    )

    assert len(evidence.candidates) == 2
    assert evidence.active_candidate_found is True
    assert evidence.resolved is True
    assert evidence.mapping_output == {'OUTPUT_VAL': 'WILDCARD_OUT'}


def test_explain_resolution_all_candidates_inactive_yields_no_active_candidate(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'OUT_A', '9', 'I'),
        (_MAPPING_NAME, 'US', '*', 'OUT_B', '1', 'I'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
    )

    assert len(evidence.candidates) == 2
    assert evidence.active_candidate_found is False
    assert evidence.resolved is False
    assert evidence.mapping_output is None


def test_explain_resolution_no_matching_candidates(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'GB', 'TRD', 'OUT', '1', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
    )

    assert evidence.candidates == ()
    assert evidence.active_candidate_found is False
    assert evidence.resolved is False
    assert evidence.mapping_output is None


def test_explain_resolution_wildcard_can_outrank_specific_by_weightage(spark):
    # Configuration bug: the wildcard row was accidentally given a higher
    # WEIGHTAGE than the specific row. Atlas's configured rule (highest
    # lexicographic WEIGHTAGE among active candidates) is authoritative,
    # so the wildcard must win even though the specific candidate is
    # "more specific".
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'SPECIFIC_OUT', '8', 'A'),
        (_MAPPING_NAME, 'US', '*', 'WILDCARD_OUT', '9', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
    )

    assert evidence.resolved is True
    assert evidence.mapping_output == {'OUTPUT_VAL': 'WILDCARD_OUT'}


def test_explain_resolution_highest_weightage_tie_raises(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'OUT_A', '9', 'A'),
        (_MAPPING_NAME, 'US', '*', 'OUT_B', '9', 'A'),
    ])

    with pytest.raises(ValueError, match='WEIGHTAGE'):
        manager.explain_resolution(
            _MAPPING_NAME,
            input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
        )


def test_explain_resolution_matches_case_insensitively(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'us', 'trd', 'OUT', '1', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD'},
    )

    assert len(evidence.candidates) == 1
    assert evidence.candidates[0].candidate_type == MappingCandidateType.SPECIFIC
    assert evidence.resolved is True


def test_explain_resolution_missing_required_input_raises(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'OUT', '1', 'A'),
    ])

    with pytest.raises(ValueError, match='FIELD_B'):
        manager.explain_resolution(
            _MAPPING_NAME,
            input_values={'FIELD_A': 'US'},
        )


def test_explain_resolution_ignores_extra_input_values(spark):
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'OUT', '1', 'A'),
    ])

    evidence = manager.explain_resolution(
        _MAPPING_NAME,
        input_values={'FIELD_A': 'US', 'FIELD_B': 'TRD', 'UNRELATED': 'ignored'},
    )

    assert evidence.resolved is True


def test_apply_ignores_inactive_rows(spark):
    # Guards against the get_mapping()/get_mapping_details() refactor
    # (shared _read_mapping_data/_fillna_mapping_columns helpers)
    # accidentally letting inactive rows into production apply().
    manager = _manager(spark, [
        (_MAPPING_NAME, 'US', 'TRD', 'OUT_A', '9', 'I'),
        (_MAPPING_NAME, 'US', '*', 'OUT_B', '1', 'I'),
    ])

    df = spark.createDataFrame(
        [('US', 'TRD')],
        ['FIELD_A', 'FIELD_B'],
    )

    result = manager.apply(df, _MAPPING_NAME)

    assert result.first()['OUTPUT_VAL'] is None
