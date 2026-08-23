import pytest

from atlas import AtlasClient


@pytest.fixture(scope='module')
def atlas(spark):
    return AtlasClient.from_csv(
        spark=spark,
        metadata_path='data/atlas/mapping_meta.csv',
        data_path='data/atlas/mapping_data.csv',
    )


def test_atlas_client_from_csv(atlas):
    mapping = atlas.get_mapping(
        'ENTITY_MAPPING'
    )

    assert (
        mapping.definition.mapping_name
        == 'ENTITY_MAPPING'
    )

    assert mapping.data.count() > 0


def test_atlas_client_apply(spark, atlas):
    mapping = atlas.get_mapping(
        'ENTITY_MAPPING'
    )

    row = mapping.data.first()

    df = spark.createDataFrame(
        [
            (
                'record-1',
                row['SRC_APP_CD'],
                row['SRC_ENTITY_CD'],
                row['DATACLASS'],
                row['COA_RULE_ID'],
            ),
        ],
        [
            'RECORD_ID',
            'SRC_APP_CD',
            'SRC_ENTITY_CD',
            'DATACLASS',
            'COA_RULE_ID',
        ],
    )

    result = atlas.apply(
        df,
        mapping_name='ENTITY_MAPPING',
    )

    assert result.count() == 1
    assert 'GL_ENTITY_CD' in result.columns
    assert 'GL_BRANCH_CD' in result.columns
