import pytest
from unittest.mock import MagicMock, patch

from core.db import PostgresConfig
from core.store import PostgresStore


CONFIG = PostgresConfig(
    host='localhost',
    port=5432,
    database='northforge_finance',
    user='leo',
    password='northforge',
)

TABLE_LOCATIONS = {
    'CFG_TRANSFORMATIONS': 'foundry_config.transformation',
}


@pytest.fixture
def mock_executor():
    with patch('core.store.postgres.PostgresExecutor') as executor_cls:
        yield executor_cls.return_value


def test_read_resolves_logical_table_to_physical_table(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        config=CONFIG,
        table_locations=TABLE_LOCATIONS,
    )

    store.read('CFG_TRANSFORMATIONS')

    spark.read.jdbc.assert_called_once_with(
        url=CONFIG.jdbc_url,
        table='foundry_config.transformation',
        properties=CONFIG.jdbc_properties,
    )


def test_write_resolves_logical_table_to_physical_table(mock_executor):
    spark = MagicMock()
    df = MagicMock()

    store = PostgresStore(
        spark=spark,
        config=CONFIG,
        table_locations=TABLE_LOCATIONS,
    )

    store.write(df, table_name='CFG_TRANSFORMATIONS')

    df.write.jdbc.assert_called_once_with(
        url=CONFIG.jdbc_url,
        table='foundry_config.transformation',
        mode='append',
        properties=CONFIG.jdbc_properties,
    )


def test_delete_uses_resolved_physical_table(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        config=CONFIG,
        table_locations=TABLE_LOCATIONS,
    )

    store.delete(
        'CFG_TRANSFORMATIONS',
        filters={'DATACLASS': 'TRIAL_BALANCE'},
    )

    sql, parameters = mock_executor.execute.call_args[0]

    assert 'foundry_config.transformation' in sql
    assert parameters == {'value_0': 'TRIAL_BALANCE'}


def test_delete_requires_at_least_one_filter(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        config=CONFIG,
        table_locations=TABLE_LOCATIONS,
    )

    with pytest.raises(ValueError):
        store.delete('CFG_TRANSFORMATIONS', filters={})


def test_read_unknown_table_raises_key_error(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        config=CONFIG,
        table_locations=TABLE_LOCATIONS,
    )

    with pytest.raises(KeyError, match='UNKNOWN'):
        store.read('UNKNOWN')


def test_delete_unknown_table_raises_key_error(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        config=CONFIG,
        table_locations=TABLE_LOCATIONS,
    )

    with pytest.raises(KeyError, match='UNKNOWN'):
        store.delete('UNKNOWN', filters={'DATACLASS': 'TRIAL_BALANCE'})
