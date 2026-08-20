import pytest

from finmap import CsvMappingRepository, MappingManager


@pytest.fixture(scope='module')
def manager(spark):
    repository = CsvMappingRepository(
        spark=spark,
        metadata_path='data/reference/mapping_meta.csv',
        data_path='data/reference/mapping_data.csv',
    )
    return MappingManager(repository)


def test_validate_entity_mapping_source_columns(spark, manager):
    df = spark.createDataFrame(
        [
            ('ADI', '100', 'TRIAL_BALANCE', 'RULE_1'),
        ],
        [
            'SRC_APP_CD',
            'SRC_ENTITY_CD',
            'DATACLASS',
            'COA_RULE_ID',
        ],
    )

    manager.validate_source_columns(
        df,
        'ENTITY_MAPPING',
    )


def test_validate_entity_mapping_missing_source_column(spark, manager):
    df = spark.createDataFrame(
        [
            ('ADI', '100', 'TRIAL_BALANCE'),
        ],
        [
            'SRC_APP_CD',
            'SRC_ENTITY_CD',
            'DATACLASS',
        ],
    )

    with pytest.raises(
        ValueError,
        match='COA_RULE_ID',
    ):
        manager.validate_source_columns(
            df,
            'ENTITY_MAPPING',
        )
