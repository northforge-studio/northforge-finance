import pytest

from atlas.repository import AtlasRepository
from core.store import CsvStore

from tests.support.fakes import FakeStore


@pytest.fixture(scope='module')
def repository(spark, atlas_meta_path, atlas_data_path):
    store = CsvStore(
        spark=spark,
        table_locations={
            'MAPPING_META': atlas_meta_path,
            'MAPPING_DATA': atlas_data_path,
        },
    )
    return AtlasRepository(store)


def test_reconstruct_entity_mapping_definition(repository):
    definition = repository.get_definition(
        'ENTITY_MAPPING',
    )

    assert definition.mapping_name == 'ENTITY_MAPPING'
    assert definition.mapping_data_name == 'NORTHFORGE_MAPPING_DATA'

    assert [
        field.logical_name
        for field in definition.lookup_fields
    ] == [
        'SRC_APP_CD',
        'SRC_ENTITY_CD',
        'DATACLASS',
    ]

    assert [
        field.logical_name
        for field in definition.informational_fields
    ] == []

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
        'GL_ENTITY_CD',
        'GL_BRANCH_CD',
        'ENTITY_SUN_ID',
        'POSTING_MEASURE_FUNC_CCY_CD',
        'WEIGHTAGE',
    ]


def test_get_definition_works_against_a_fake_store(spark):
    meta_df = spark.createDataFrame(
        [
            ('ENTITY_MAPPING', 'ENTITY_MAPPING_DATASET', 'SRC_APP_CD', 'SRC_APP_CD', 'INPUT', 'VALUE', 'SRC_APP_CD', 'STRING', 1),
        ],
        [
            'MAPPING_NAME',
            'MAPPING_DATA_NAME',
            'METADATA_FIELD_NAME',
            'LOGICAL_FIELD_NAME',
            'FIELD_TYPE',
            'LOOKUP_TYPE',
            'SRC_FIELD_NAME',
            'DATATYPE',
            'UI_FIELD_ORDER',
        ],
    )

    store = FakeStore({'MAPPING_META': meta_df})
    repository = AtlasRepository(store)

    definition = repository.get_definition('ENTITY_MAPPING')

    assert definition.mapping_name == 'ENTITY_MAPPING'
    assert definition.mapping_data_name == 'ENTITY_MAPPING_DATASET'
