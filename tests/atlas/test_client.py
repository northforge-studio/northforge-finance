import pytest

from atlas import AtlasClient


@pytest.fixture(scope='module')
def atlas(spark, atlas_meta_path, atlas_data_path):
    return AtlasClient.from_csv(
        spark=spark,
        metadata_path=atlas_meta_path,
        data_path=atlas_data_path,
    )


def test_from_csv_loads_mapping_definition_and_data(atlas):
    mapping = atlas.get_mapping('ENTITY_MAPPING')

    assert mapping.definition.mapping_name == 'ENTITY_MAPPING'

    assert mapping.data.count() > 0


def test_apply_adds_mapping_output_columns(spark, atlas):
    mapping = atlas.get_mapping('ENTITY_MAPPING')

    row = mapping.data.first()

    df = spark.createDataFrame(
        [
            (
                'record-1',
                row['SRC_APP_CD'],
                row['SRC_ENTITY_CD'],
                row['DATACLASS'],
            ),
        ],
        schema=[
            'RECORD_ID',
            'SRC_APP_CD',
            'SRC_ENTITY_CD',
            'DATACLASS',
        ],
    )

    result = atlas.apply(df, mapping_name='ENTITY_MAPPING')

    assert result.count() == 1
    assert 'GL_ENTITY_CD' in result.columns
    assert 'GL_BRANCH_CD' in result.columns
