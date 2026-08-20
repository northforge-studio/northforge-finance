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

    mapping = manager.get_mapping('ENTITY_MAPPING')

    manager.validate(
        df,
        mapping
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

        mapping = manager.get_mapping('ENTITY_MAPPING')

        manager.validate(
            df,
            mapping,
        )


def test_apply_resolves_wildcard_by_weightage(spark, manager):
    df = spark.createDataFrame(
        [
            (
                'record-1',
                '11392',
                'NSA',
                'TRIAL_BALANCE',
                '',
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

    result = manager.apply(
        df,
        'ENTITY_MAPPING',
    )

    result.show(
        truncate=False,
    )

    assert result.count() == 1

    assert result.columns == [
        'RECORD_ID',
        'SRC_APP_CD',
        'SRC_ENTITY_CD',
        'DATACLASS',
        'COA_RULE_ID',
        'GL_ENTITY_CD',
        'GL_BRANCH_CD',
        'ENTITY_SUN_ID',
        'POSTING_MEASURE_FUNC_CCY_CD',
    ]


def test_apply_preserves_unmatched_source_row(spark, manager):
    df = spark.createDataFrame(
        [
            (
                'record-1',
                '11010',
                'NSA',
                'TRIAL_BALANCE',
                '',
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

    result = manager.apply(
        df,
        'ENTITY_MAPPING',
    )

    row = result.first()

    assert row['RECORD_ID'] == 'record-1'
    assert row['GL_ENTITY_CD'] is None
    assert row['GL_BRANCH_CD'] is None


def test_apply_rejects_existing_output_column(spark, manager):
    df = spark.createDataFrame(
        [
            (
                'APP',
                '100',
                'TRIAL_BALANCE',
                'RULE',
                'existing',
            ),
        ],
        [
            'SRC_APP_CD',
            'SRC_ENTITY_CD',
            'DATACLASS',
            'COA_RULE_ID',
            'GL_ENTITY_CD',
        ],
    )

    with pytest.raises(
        ValueError,
        match='output columns already exist',
    ):
        manager.apply(
            df,
            'ENTITY_MAPPING',
        )
