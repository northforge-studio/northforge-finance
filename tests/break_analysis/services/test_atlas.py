from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from pyspark.sql.types import DateType, StringType, StructField, StructType

from atlas.models import FieldType, LookupType, MappingDefinition, MappingField

from break_analysis.services.atlas import AtlasEvidenceService
from break_analysis.models import BreakRecord

from gl.models import GLSegments


AS_OF_DATE = date(2026, 1, 1)

_DEFAULT_SEGMENT_VALUES = dict(
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
    def __init__(self, definition: MappingDefinition):
        self._definition = definition

    def get_definition(self, mapping_name: str) -> MappingDefinition:
        return self._definition


class _FakeFoundryRepository:
    def __init__(self, df):
        self._df = df

    def read_posting(self, workflow_run_id):
        return self._df


def _segments(**overrides) -> GLSegments:
    values = dict(_DEFAULT_SEGMENT_VALUES)
    values.update(overrides)
    return GLSegments(**values)


def _break_record(**overrides) -> BreakRecord:
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


def _mapping_definition(
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


def _posting_row(**overrides) -> dict:
    row = dict(
        AS_OF_DT=AS_OF_DATE,
        POSTING_MEASURE_FUNC_CCY_CD='USD',
        **_POSTING_SEGMENT_COLUMNS,
        COUNTRY_CD='US',
        COUNTERPARTY_CD='1000',
    )
    row.update(overrides)
    return row


def _postings_df(spark, rows: list[dict]):
    return spark.createDataFrame(
        [tuple(row[field.name] for field in _POSTING_SCHEMA.fields) for row in rows],
        schema=_POSTING_SCHEMA,
    )


def _service(definition: MappingDefinition, df) -> AtlasEvidenceService:
    return AtlasEvidenceService(
        atlas_client=_FakeAtlasClient(definition),
        foundry_repository=_FakeFoundryRepository(df),
    )


def test_input_field_discovery_uses_exact_canonical_names(spark):
    definition = _mapping_definition(
        input_field_names=('COUNTRY_CD', 'COUNTERPARTY_CD'),
    )
    df = _postings_df(spark, [_posting_row()])
    service = _service(definition, df)

    result = service.get_mapping_input_values(
        _break_record(), mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert set(result[0].values.keys()) == {'COUNTRY_CD', 'COUNTERPARTY_CD'}


def test_single_foundry_match_returns_one_evidence_result(spark):
    definition = _mapping_definition()
    df = _postings_df(spark, [_posting_row()])
    service = _service(definition, df)

    result = service.get_mapping_input_values(
        _break_record(), mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert result[0].values == {'COUNTRY_CD': 'US', 'COUNTERPARTY_CD': '1000'}
    assert result[0].source_record_count == 1


def test_duplicate_input_combinations_are_collapsed_with_count(spark):
    definition = _mapping_definition()
    df = _postings_df(
        spark,
        [
            _posting_row(),
            _posting_row(),
            _posting_row(),
            _posting_row(),
        ],
    )
    service = _service(definition, df)

    result = service.get_mapping_input_values(
        _break_record(), mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert result[0].values == {'COUNTRY_CD': 'US', 'COUNTERPARTY_CD': '1000'}
    assert result[0].source_record_count == 4


def test_multiple_distinct_input_combinations_produce_multiple_results(spark):
    definition = _mapping_definition()
    df = _postings_df(
        spark,
        [
            _posting_row(COUNTRY_CD='US', COUNTERPARTY_CD='1000'),
            _posting_row(COUNTRY_CD='US', COUNTERPARTY_CD='1000'),
            _posting_row(COUNTRY_CD='US', COUNTERPARTY_CD='2000'),
        ],
    )
    service = _service(definition, df)

    result = service.get_mapping_input_values(
        _break_record(), mapping_name='TEST_MAPPING',
    )

    by_counterparty = {r.values['COUNTERPARTY_CD']: r for r in result}
    assert len(result) == 2
    assert by_counterparty['1000'].source_record_count == 2
    assert by_counterparty['2000'].source_record_count == 1


def test_blank_gl_segment_matches_empty_string_in_foundry(spark):
    definition = _mapping_definition()
    break_record = _break_record(segments=_segments(sub_account=''))
    df = _postings_df(
        spark,
        [_posting_row(GL_SUB_ACCOUNT='')],
    )
    service = _service(definition, df)

    result = service.get_mapping_input_values(
        break_record, mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert result[0].source_record_count == 1


def test_nonmatching_segments_are_excluded(spark):
    definition = _mapping_definition()
    df = _postings_df(
        spark,
        [
            _posting_row(),
            _posting_row(GL_ENTITY_CD='OTHER'),
            _posting_row(GL_BRANCH_CD='999'),
        ],
    )
    service = _service(definition, df)

    result = service.get_mapping_input_values(
        _break_record(), mapping_name='TEST_MAPPING',
    )

    assert len(result) == 1
    assert result[0].source_record_count == 1


def test_no_matching_foundry_rows_raises(spark):
    definition = _mapping_definition()
    df = _postings_df(
        spark,
        [_posting_row(GL_ENTITY_CD='UNRELATED')],
    )
    service = _service(definition, df)

    with pytest.raises(ValueError):
        service.get_mapping_input_values(
            _break_record(), mapping_name='TEST_MAPPING',
        )


def test_missing_required_atlas_input_column_raises(spark):
    definition = _mapping_definition(
        input_field_names=('COUNTRY_CD', 'MISSING_COLUMN'),
    )
    df = _postings_df(spark, [_posting_row()])
    service = _service(definition, df)

    with pytest.raises(ValueError):
        service.get_mapping_input_values(
            _break_record(), mapping_name='TEST_MAPPING',
        )


def test_mapping_with_no_input_fields_raises(spark):
    definition = _mapping_definition(input_field_names=())
    df = _postings_df(spark, [_posting_row()])
    service = _service(definition, df)

    with pytest.raises(ValueError):
        service.get_mapping_input_values(
            _break_record(), mapping_name='TEST_MAPPING',
        )
