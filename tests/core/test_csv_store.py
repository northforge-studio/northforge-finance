import pytest
from pyspark.sql.types import StructType, StructField, StringType

from core.store import CsvStore


SCHEMA = StructType([
    StructField('BUSINESS_DT', StringType(), True),
    StructField('BATCH_ID', StringType(), True),
    StructField('NAME', StringType(), True),
])


def _write_csv(path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write('BUSINESS_DT,BATCH_ID,NAME\n')
        for row in rows:
            f.write(','.join(row) + '\n')


def test_read_applies_schema_and_fills_string_nulls(spark, tmp_path):
    csv_path = tmp_path / 'TABLE' / 'data.csv'
    _write_csv(
        csv_path,
        [
            ('2025-03-31', '1', ''),
            ('2025-03-31', '2', 'present'),
        ],
    )

    store = CsvStore(spark, table_locations={'TABLE': csv_path})

    df = store.read('TABLE', schema=SCHEMA)

    assert df.columns == SCHEMA.fieldNames()
    assert [f.dataType for f in df.schema.fields] == [f.dataType for f in SCHEMA.fields]

    rows = {row['BATCH_ID']: row['NAME'] for row in df.collect()}
    assert rows['1'] == ''
    assert rows['2'] == 'present'


def test_read_missing_table_with_schema_returns_empty_dataframe(spark, tmp_path):
    csv_path = tmp_path / 'MISSING' / 'data.csv'

    store = CsvStore(spark, table_locations={'MISSING': csv_path})

    df = store.read('MISSING', schema=SCHEMA)

    assert df.schema == SCHEMA
    assert df.count() == 0


def test_write_default_mode_appends(spark, tmp_path):
    csv_path = tmp_path / 'TABLE'

    store = CsvStore(spark, table_locations={'TABLE': csv_path})

    df = spark.createDataFrame(
        [('2025-03-31', '1', 'first')],
        schema=['BUSINESS_DT', 'BATCH_ID', 'NAME'],
    )

    store.write(df, table_name='TABLE')
    store.write(df, table_name='TABLE')

    result = store.read('TABLE', schema=SCHEMA)
    assert result.count() == 2


def test_delete_removes_only_rows_matching_all_filters(spark, tmp_path):
    csv_path = tmp_path / 'TABLE' / 'data.csv'
    _write_csv(
        csv_path,
        [
            ('2025-03-31', '1', 'a'),
            ('2025-03-31', '2', 'b'),
            ('2025-04-01', '1', 'c'),
        ],
    )

    store = CsvStore(spark, table_locations={'TABLE': csv_path})

    store.delete(
        'TABLE',
        filters={'BUSINESS_DT': '2025-03-31', 'BATCH_ID': '1'},
        schema=SCHEMA,
    )

    remaining = store.read('TABLE', schema=SCHEMA)
    remaining_names = {row['NAME'] for row in remaining.collect()}

    assert remaining_names == {'b', 'c'}


def test_delete_returns_without_error_when_path_missing(spark, tmp_path):
    csv_path = tmp_path / 'MISSING'

    store = CsvStore(spark, table_locations={'MISSING': csv_path})

    store.delete(
        'MISSING',
        filters={'BUSINESS_DT': '2025-03-31'},
        schema=SCHEMA,
    )


def test_delete_requires_at_least_one_filter(spark, tmp_path):
    csv_path = tmp_path / 'TABLE' / 'data.csv'
    _write_csv(csv_path, [('2025-03-31', '1', 'a')])

    store = CsvStore(spark, table_locations={'TABLE': csv_path})

    with pytest.raises(ValueError, match='at least one filter'):
        store.delete('TABLE', filters={}, schema=SCHEMA)


def test_read_unknown_table_raises_key_error(spark, tmp_path):
    store = CsvStore(spark, table_locations={'TABLE': tmp_path / 'TABLE'})

    with pytest.raises(KeyError, match='UNKNOWN'):
        store.read('UNKNOWN', schema=SCHEMA)
