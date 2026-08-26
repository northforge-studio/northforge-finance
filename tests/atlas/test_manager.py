import pytest

from atlas.manager import MappingManager
from atlas.models import PostingRule, GatewayRule
from atlas.repository import AtlasRepository
from core.store import CsvStore


def _make_repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            'MAPPING_META': 'data/atlas/mapping_meta.csv',
            'MAPPING_DATA': 'data/atlas/mapping_data.csv',
        },
    )
    return AtlasRepository(store)


@pytest.fixture(scope='module')
def manager(spark):
    repository = _make_repository(spark)
    return MappingManager(repository)


def test_validate_entity_mapping_source_columns(spark, manager):
    df = spark.createDataFrame(
        [
            ('SRC_SYS', '100', 'TRIAL_BALANCE', 'RULE_1'),
        ],
        [
            'SRC_APP_CD',
            'SRC_ENTITY_CD',
            'DATACLASS',
            'COA_RULE_ID',
        ],
    )

    mapping = manager.get_mapping('ENTITY_MAPPING')

    manager._validate(
        df,
        mapping
    )


def test_validate_entity_mapping_missing_source_column(spark, manager):
    df = spark.createDataFrame(
        [
            ('SRC_SYS', '100'),
        ],
        [
            'SRC_APP_CD',
            'SRC_ENTITY_CD',
        ],
    )

    with pytest.raises(
        ValueError,
        match='DATACLASS',
    ):

        mapping = manager.get_mapping('ENTITY_MAPPING')

        manager._validate(
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


def test_apply_auto_drops_existing_output_column(spark, manager):
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

    result = manager.apply(
            df,
            'ENTITY_MAPPING',
        )

    result.show(
        truncate=False,
    )

    assert result.count() == 1

    assert result.columns == [
        'SRC_APP_CD',
        'SRC_ENTITY_CD',
        'DATACLASS',
        'COA_RULE_ID',
        'GL_ENTITY_CD',
        'GL_BRANCH_CD',
        'ENTITY_SUN_ID',
        'POSTING_MEASURE_FUNC_CCY_CD',
    ]


def test_get_rule_config_groups_posting_rules_by_gateway_rule_id(manager):
    rule_cfg = manager.get_rule_config('TRIAL_BALANCE')

    assert rule_cfg == [
        GatewayRule(
            id='TB-GROSS-UP',
            posting_measure_nm='ADJUSTED_BALANCE',
            posting_rules=(
                PostingRule(
                    id='TB-GROSS-UP',
                    posting_stream='GROSS_UP',
                ),
            ),
        )
    ]


def test_get_rule_config_unmatched_dataclass_returns_empty(manager):
    rule_cfg = manager.get_rule_config('NON_EXISTENT_DATACLASS')

    assert rule_cfg == []
