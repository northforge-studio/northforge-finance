import pytest
from pyspark.sql import DataFrame
from pyspark.sql.types import DateType, StringType, StructField, StructType

from atlas.models import (
    FieldType,
    LookupType,
    MappingDefinition,
    MappingField,
    MappingResolutionEvidence,
)
from break_analysis.services.atlas import AtlasEvidenceService
from registry.models import GLSegmentType

from tests.break_analysis.factories import make_break_record, make_segments
from tests.support.constants import AS_OF_DATE


_POSTING_SEGMENT_COLUMNS = dict(
    GL_ENTITY_CD='USM',
    GL_BRANCH_CD='100',
    GL_DEPT_CD='4000',
    GL_ACCOUNT='123456',
    GL_SUB_ACCOUNT='001',
    GL_AFFILIATE_CD='AFF1',
    GL_PRODUCT_CD='PRD1',
    GL_BOOK_CD='BK1',
    GL_COA_SRC_SEGMENT='SRC1',
)

_POSTING_SCHEMA = StructType([
    StructField('AS_OF_DT', DateType(), False),
    StructField('POSTING_MEASURE_FUNC_CCY_CD', StringType(), False),
    StructField('GL_ENTITY_CD', StringType(), False),
    StructField('GL_BRANCH_CD', StringType(), False),
    StructField('GL_DEPT_CD', StringType(), False),
    StructField('GL_ACCOUNT', StringType(), False),
    StructField('GL_SUB_ACCOUNT', StringType(), False),
    StructField('GL_AFFILIATE_CD', StringType(), False),
    StructField('GL_PRODUCT_CD', StringType(), False),
    StructField('GL_BOOK_CD', StringType(), False),
    StructField('GL_COA_SRC_SEGMENT', StringType(), False),
    StructField('COUNTRY_CD', StringType(), False),
    StructField('COUNTERPARTY_CD', StringType(), False),
])


class _FakeAtlasClient:
    '''Duck-types AtlasClient, serving a canned definition and resolutions.'''

    def __init__(
        self,
        definition: MappingDefinition,
        resolutions: dict[tuple, MappingResolutionEvidence] | None = None,
    ):
        self._definition = definition
        self._resolutions = resolutions or {}
        self.explain_resolution_calls: list[dict] = []


    def get_definition(self, mapping_name: str) -> MappingDefinition:
        return self._definition


    def explain_resolution(
        self,
        mapping_name: str,
        input_values: dict[str, str],
    ) -> MappingResolutionEvidence:
        self.explain_resolution_calls.append(
            dict(mapping_name=mapping_name, input_values=input_values)
        )
        return self._resolutions[tuple(sorted(input_values.items()))]


class _FakeFoundryRepository:
    '''Duck-types the Foundry repository read of the posting zone.'''

    def __init__(self, df):
        self._df = df


    def read_posting(self, workflow_run_id):
        return self._df


def _make_mapping_definition(
    mapping_name: str = 'TEST_MAPPING',
    input_field_names: tuple[str, ...] = ('COUNTRY_CD', 'COUNTERPARTY_CD'),
) -> MappingDefinition:
    input_fields = tuple(
        MappingField(
            physical_name=f'INPUT_COL{i + 1}',
            logical_name=name,
            field_type=FieldType.INPUT,
            lookup_type=LookupType.VALUE,
            src_field_name=name,
            datatype='STRING',
            order=i + 1,
        )
        for i, name in enumerate(input_field_names)
    )

    output_field = MappingField(
        physical_name='OUTPUT_COL1',
        logical_name='OUTPUT_VALUE',
        field_type=FieldType.OUTPUT,
        lookup_type=LookupType.VALUE,
        src_field_name=None,
        datatype='STRING',
        order=len(input_fields) + 1,
    )

    return MappingDefinition(
        mapping_name=mapping_name,
        mapping_data_name='TEST_MAPPING_DATA',
        fields=(*input_fields, output_field),
    )


def _make_posting_row(**overrides) -> dict:
    row = dict(
        AS_OF_DT=AS_OF_DATE,
        POSTING_MEASURE_FUNC_CCY_CD='USD',
        **_POSTING_SEGMENT_COLUMNS,
        COUNTRY_CD='US',
        COUNTERPARTY_CD='1000',
    )
    row.update(overrides)
    return row


def _make_postings_df(spark, rows: list[dict]) -> DataFrame:
    return spark.createDataFrame(
        [tuple(row[field.name] for field in _POSTING_SCHEMA.fields) for row in rows],
        schema=_POSTING_SCHEMA,
    )


def _make_service(
    definition: MappingDefinition,
    df,
    resolutions: dict[tuple, MappingResolutionEvidence] | None = None,
) -> AtlasEvidenceService:
    return AtlasEvidenceService(
        atlas_client=_FakeAtlasClient(definition, resolutions),
        foundry_repository=_FakeFoundryRepository(df),
    )


def _make_resolution(
    mapping_name: str, values: dict[str, str], output: str,
) -> MappingResolutionEvidence:
    return MappingResolutionEvidence(
        mapping_name=mapping_name,
        input_values=values,
        candidates=(),
        active_candidate_found=True,
        resolved=True,
        mapping_output={'OUTPUT_VALUE': output},
    )


def test_get_foundry_mapping_input_values_uses_exact_canonical_input_names(spark):
    definition = _make_mapping_definition(
        input_field_names=('COUNTRY_CD', 'COUNTERPARTY_CD'),
    )
    df = _make_postings_df(spark, [_make_posting_row()])
    service = _make_service(definition, df)

    result = service.get_foundry_mapping_input_values(
        make_break_record(), mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert set(result[0].values.keys()) == {'COUNTRY_CD', 'COUNTERPARTY_CD'}


def test_get_foundry_mapping_input_values_single_match_returns_one_result(spark):
    definition = _make_mapping_definition()
    df = _make_postings_df(spark, [_make_posting_row()])
    service = _make_service(definition, df)

    result = service.get_foundry_mapping_input_values(
        make_break_record(), mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert result[0].values == {'COUNTRY_CD': 'US', 'COUNTERPARTY_CD': '1000'}
    assert result[0].source_record_count == 1


def test_get_foundry_mapping_input_values_collapses_duplicates_with_count(spark):
    definition = _make_mapping_definition()
    df = _make_postings_df(
        spark,
        [
            _make_posting_row(),
            _make_posting_row(),
            _make_posting_row(),
            _make_posting_row(),
        ],
    )
    service = _make_service(definition, df)

    result = service.get_foundry_mapping_input_values(
        make_break_record(), mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert result[0].values == {'COUNTRY_CD': 'US', 'COUNTERPARTY_CD': '1000'}
    assert result[0].source_record_count == 4


def test_get_foundry_mapping_input_values_returns_one_result_per_combination(spark):
    definition = _make_mapping_definition()
    df = _make_postings_df(
        spark,
        [
            _make_posting_row(COUNTRY_CD='US', COUNTERPARTY_CD='1000'),
            _make_posting_row(COUNTRY_CD='US', COUNTERPARTY_CD='1000'),
            _make_posting_row(COUNTRY_CD='US', COUNTERPARTY_CD='2000'),
        ],
    )
    service = _make_service(definition, df)

    result = service.get_foundry_mapping_input_values(
        make_break_record(), mapping_name='TEST_MAPPING',
    )

    by_counterparty = {r.values['COUNTERPARTY_CD']: r for r in result}
    assert len(result) == 2
    assert by_counterparty['1000'].source_record_count == 2
    assert by_counterparty['2000'].source_record_count == 1


def test_get_foundry_mapping_input_values_blank_segment_matches_empty_string(spark):
    definition = _make_mapping_definition()
    break_record = make_break_record(segments=make_segments(sub_account=''))
    df = _make_postings_df(
        spark,
        [_make_posting_row(GL_SUB_ACCOUNT='')],
    )
    service = _make_service(definition, df)

    result = service.get_foundry_mapping_input_values(
        break_record, mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert result[0].source_record_count == 1


def test_get_foundry_mapping_input_values_excludes_nonmatching_segments(spark):
    definition = _make_mapping_definition()
    df = _make_postings_df(
        spark,
        [
            _make_posting_row(),
            _make_posting_row(GL_ENTITY_CD='OTHER'),
            _make_posting_row(GL_BRANCH_CD='999'),
        ],
    )
    service = _make_service(definition, df)

    result = service.get_foundry_mapping_input_values(
        make_break_record(), mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert result[0].source_record_count == 1


def test_get_foundry_mapping_input_values_no_matching_rows_raises(spark):
    definition = _make_mapping_definition()
    df = _make_postings_df(
        spark,
        [_make_posting_row(GL_ENTITY_CD='UNRELATED')],
    )
    service = _make_service(definition, df)

    with pytest.raises(ValueError, match='No foundry_posting rows found'):
        service.get_foundry_mapping_input_values(
            make_break_record(), mapping_name='TEST_MAPPING',
        )


def test_get_foundry_mapping_input_values_missing_input_column_raises(spark):
    definition = _make_mapping_definition(
        input_field_names=('COUNTRY_CD', 'MISSING_COLUMN'),
    )
    df = _make_postings_df(spark, [_make_posting_row()])
    service = _make_service(definition, df)

    with pytest.raises(ValueError, match='requires foundry_posting columns'):
        service.get_foundry_mapping_input_values(
            make_break_record(), mapping_name='TEST_MAPPING',
        )


def test_get_foundry_mapping_input_values_mapping_without_input_fields_raises(spark):
    definition = _make_mapping_definition(input_field_names=())
    df = _make_postings_df(spark, [_make_posting_row()])
    service = _make_service(definition, df)

    with pytest.raises(ValueError, match='has no input fields'):
        service.get_foundry_mapping_input_values(
            make_break_record(), mapping_name='TEST_MAPPING',
        )


def test_investigate_resolution_wraps_single_foundry_input_with_its_resolution(spark):
    # investigate_resolution() derives the mapping name from segment_type
    # (SEGMENT_MAPPING_NAMES); GLSegmentType.ENTITY maps to ENTITY_MAPPING.
    definition = _make_mapping_definition(mapping_name='ENTITY_MAPPING')
    df = _make_postings_df(spark, [_make_posting_row()])
    values = {'COUNTRY_CD': 'US', 'COUNTERPARTY_CD': '1000'}
    resolution = _make_resolution('ENTITY_MAPPING', values, output='RESOLVED_A')
    service = _make_service(
        definition, df,
        resolutions={tuple(sorted(values.items())): resolution},
    )
    break_record = make_break_record()

    evidence = service.investigate_resolution(
        break_record,
        segment_type=GLSegmentType.ENTITY,
    )

    assert evidence.recon_result_id == break_record.recon_result_id
    assert evidence.segment_type == GLSegmentType.ENTITY
    assert evidence.mapping_name == 'ENTITY_MAPPING'
    assert len(evidence.input_resolutions) == 1
    assert evidence.input_resolutions[0].foundry_inputs.values == values
    assert evidence.input_resolutions[0].resolution is resolution


def test_investigate_resolution_pairs_each_foundry_input_with_its_own_resolution(spark):
    definition = _make_mapping_definition(mapping_name='ENTITY_MAPPING')
    df = _make_postings_df(
        spark,
        [
            _make_posting_row(COUNTRY_CD='US', COUNTERPARTY_CD='1000'),
            _make_posting_row(COUNTRY_CD='US', COUNTERPARTY_CD='2000'),
        ],
    )
    values_a = {'COUNTRY_CD': 'US', 'COUNTERPARTY_CD': '1000'}
    values_b = {'COUNTRY_CD': 'US', 'COUNTERPARTY_CD': '2000'}
    resolution_a = _make_resolution('ENTITY_MAPPING', values_a, output='RESOLVED_A')
    resolution_b = _make_resolution('ENTITY_MAPPING', values_b, output='RESOLVED_B')
    service = _make_service(
        definition, df,
        resolutions={
            tuple(sorted(values_a.items())): resolution_a,
            tuple(sorted(values_b.items())): resolution_b,
        },
    )

    evidence = service.investigate_resolution(
        make_break_record(),
        segment_type=GLSegmentType.ENTITY,
    )

    by_counterparty = {
        input_resolution.foundry_inputs.values['COUNTERPARTY_CD']: input_resolution
        for input_resolution in evidence.input_resolutions
    }
    assert len(by_counterparty) == 2
    assert by_counterparty['1000'].resolution is resolution_a
    assert by_counterparty['2000'].resolution is resolution_b


def test_investigate_resolution_propagates_foundry_lookup_error(spark):
    definition = _make_mapping_definition(mapping_name='ENTITY_MAPPING')
    df = _make_postings_df(
        spark,
        [_make_posting_row(GL_ENTITY_CD='UNRELATED')],
    )
    service = _make_service(definition, df)

    with pytest.raises(ValueError, match='No foundry_posting rows found'):
        service.investigate_resolution(
            make_break_record(),
            segment_type=GLSegmentType.ENTITY,
        )
