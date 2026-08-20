import pytest

from finmap import FinMapClient


@pytest.fixture(scope='module')
def finmap(spark):
    return FinMapClient.from_csv(
        spark=spark,
        metadata_path='data/reference/mapping_meta.csv',
        data_path='data/reference/mapping_data.csv',
    )


def test_finmap_client_from_csv(finmap):
    mapping = finmap.get_mapping(
        'ENTITY_MAPPING'
    )

    assert (
        mapping.definition.mapping_name
        == 'ENTITY_MAPPING'
    )

    assert mapping.data.count() > 0


def test_finmap_client_apply(spark, finmap):
    mapping = finmap.get_mapping(
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

    result = finmap.apply(
        df,
        mapping_name='ENTITY_MAPPING',
    )

    assert result.count() == 1
    assert 'GL_ENTITY_CD' in result.columns
    assert 'GL_BRANCH_CD' in result.columns
