import pytest
from unittest.mock import MagicMock, patch

from pyspark.sql.types import (
    IntegerType,
    StringType,
    StructField,
    StructType,
)

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
    'CFG_TRANSFORMATIONS': 'spec.transformation',
}


@pytest.fixture
def mock_executor():
    with patch('core.store.postgres.PostgresExecutor') as executor_cls:
        yield executor_cls.return_value


def test_read_resolves_logical_table_to_physical_table(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        table_names=TABLE_LOCATIONS,
    )

    store.read('CFG_TRANSFORMATIONS')

    spark.read.jdbc.assert_called_once_with(
        url=CONFIG.jdbc_url,
        table='spec.transformation',
        properties=CONFIG.jdbc_properties,
    )


def test_write_resolves_logical_table_to_physical_table(mock_executor):
    spark = MagicMock()
    df = MagicMock()
    df.columns = ['SRC_APP_CD', 'DATACLASS']

    store = PostgresStore(
        spark=spark,
        table_names=TABLE_LOCATIONS,
    )

    store.write(df, table_name='CFG_TRANSFORMATIONS')

    df.toDF.assert_called_once_with('src_app_cd', 'dataclass')

    lowered_df = df.toDF.return_value
    lowered_df.write.jdbc.assert_called_once_with(
        url=CONFIG.jdbc_url,
        table='spec.transformation',
        mode='append',
        properties=CONFIG.jdbc_properties,
    )


def test_write_fills_null_string_columns_with_empty_string(mock_executor, spark):
    schema = StructType([
        StructField('SRC_ACCOUNT_ID', StringType(), nullable=True),
        StructField('OUTPUT_COL6', StringType(), nullable=True),
        StructField('AMOUNT', IntegerType(), nullable=True),
    ])

    df = spark.createDataFrame(
        [('11392', None, None)],
        schema=schema,
    )

    store = PostgresStore(
        spark=spark,
        table_names=TABLE_LOCATIONS,
    )

    filled = store._fill_null_strings(df)

    rows = filled.collect()

    assert rows[0]['SRC_ACCOUNT_ID'] == '11392'
    assert rows[0]['OUTPUT_COL6'] == ''
    assert rows[0]['AMOUNT'] is None


def test_delete_uses_resolved_physical_table(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        table_names=TABLE_LOCATIONS,
    )

    store.delete(
        'CFG_TRANSFORMATIONS',
        filters={'DATACLASS': 'TRIAL_BALANCE'},
    )

    sql, parameters = mock_executor.execute.call_args[0]

    assert 'spec.transformation' in sql
    assert parameters == {'value_0': 'TRIAL_BALANCE'}


def test_delete_lowercases_filter_column_names_in_sql(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        table_names=TABLE_LOCATIONS,
    )

    store.delete(
        'CFG_TRANSFORMATIONS',
        filters={'BUSINESS_DT': '2026-08-24', 'BATCH_ID': '1'},
    )

    sql, _ = mock_executor.execute.call_args[0]

    assert '"business_dt"' in sql
    assert '"batch_id"' in sql
    assert '"BUSINESS_DT"' not in sql
    assert '"BATCH_ID"' not in sql


def test_delete_requires_at_least_one_filter(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        table_names=TABLE_LOCATIONS,
    )

    with pytest.raises(ValueError):
        store.delete('CFG_TRANSFORMATIONS', filters={})


def test_read_unknown_table_raises_key_error(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        table_names=TABLE_LOCATIONS,
    )

    with pytest.raises(KeyError, match='UNKNOWN'):
        store.read('UNKNOWN')


def test_delete_unknown_table_raises_key_error(mock_executor):
    spark = MagicMock()

    store = PostgresStore(
        spark=spark,
        table_names=TABLE_LOCATIONS,
    )

    with pytest.raises(KeyError, match='UNKNOWN'):
        store.delete('UNKNOWN', filters={'DATACLASS': 'TRIAL_BALANCE'})
