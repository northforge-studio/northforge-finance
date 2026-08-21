import pytest

from finmap.repository import CsvRepository


@pytest.fixture(scope='module')
def repository(spark):
    return CsvRepository(
        spark=spark,
        metadata_path='data/reference/mapping_meta.csv',
        data_path='data/reference/mapping_data.csv',
    )


def test_reconstruct_entity_mapping_definition(repository):
    definition = repository.get_definition(
        'ENTITY_MAPPING',
    )

    assert definition.mapping_name == 'ENTITY_MAPPING'
    assert definition.mapping_data_name == 'ENTITY_MAPPING_DATASET'

    assert [
        field.logical_name
        for field in definition.lookup_fields
    ] == [
        'SRC_APP_CD',
        'SRC_ENTITY_CD',
        'DATACLASS',
        'COA_RULE_ID',
    ]

    assert [
        field.logical_name
        for field in definition.informational_fields
    ] == [
        'SOURCE_SYSTEM_NAME',
        'ENTITY_NAME',
        'RULE_ID_DESC',
    ]

    assert [
        field.logical_name
        for field in definition.output_fields
    ] == [
        'GL_ENTITY_CD',
        'GL_BRANCH_CD',
        'ENTITY_SUN_ID',
        'POSTING_MEASURE_FUNC_CCY_CD',
    ]


def test_reconstruct_entity_mapping_data(repository):
    mapping = repository.get_mapping(
        'ENTITY_MAPPING',
    )

    assert mapping.definition.mapping_name == 'ENTITY_MAPPING'

    assert mapping.data.columns == [
        'SRC_APP_CD',
        'SRC_ENTITY_CD',
        'DATACLASS',
        'COA_RULE_ID',
        'SOURCE_SYSTEM_NAME',
        'ENTITY_NAME',
        'RULE_ID_DESC',
        'GL_ENTITY_CD',
        'GL_BRANCH_CD',
        'ENTITY_SUN_ID',
        'POSTING_MEASURE_FUNC_CCY_CD',
        'WEIGHTAGE',
    ]
