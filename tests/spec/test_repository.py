import pytest
from unittest.mock import MagicMock, patch

from core.db import PostgresConfig
from core.store import CsvStore, PostgresStore

from spec.models import FileLayout, FileLayoutField
from spec.repository import SpecRepository


CONFIG = PostgresConfig(
    host='localhost',
    port=5432,
    database='northforge_finance',
    user='leo',
    password='northforge',
)

POSTGRES_TABLE_LOCATIONS = {
    'CFG_TRANSFORMATIONS': 'spec.transformation',
    'CFG_FILE_LAYOUT': 'spec.file_layout',
}


def _write_transformations_csv(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(
            'SRC_APP_CD,DATACLASS,OUTPUT_COL_NAME,SEQ,ZONE,STAGE,'
            'SUB_STAGE,EXPRESSION,STATUS\n'
            '11392,TRIAL_BALANCE,DATACLASS,1,FOUNDRY,STAGING,,'
            "'TRIAL_BALANCE',A\n"
        )


def _write_file_layout_csv(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(
            'SRC_APP_CD,DATACLASS,COLUMN_NAME,LOGICAL_COLUMN_NAME,SEQ,'
            'DATATYPE,STATUS\n'
            '11392,TRIAL_BALANCE,SRC_ACCOUNT_ID,SRC_ACCOUNT_ID,1,STRING,A\n'
            '11392,TRIAL_BALANCE,SRC_ACCOUNT_NM,SRC_ACCOUNT_NM,2,STRING,A\n'
        )


def test_get_transformations_reads_configured_logical_table_from_csv(spark, tmp_path):
    csv_path = tmp_path / 'CFG_TRANSFORMATIONS' / 'data.csv'
    _write_transformations_csv(csv_path)

    store = CsvStore(
        spark=spark,
        table_locations={'CFG_TRANSFORMATIONS': csv_path},
    )

    repository = SpecRepository(store)

    rows = repository.get_transformations(
        dataclass='TRIAL_BALANCE',
        zone='FOUNDRY',
        stage='STAGING',
    )

    assert rows == [
        {
            'SRC_APP_CD': '11392',
            'DATACLASS': 'TRIAL_BALANCE',
            'OUTPUT_COL_NAME': 'DATACLASS',
            'SEQ': 1,
            'ZONE': 'FOUNDRY',
            'STAGE': 'STAGING',
            'SUB_STAGE': '',
            'EXPRESSION': "'TRIAL_BALANCE'",
            'STATUS': 'A',
        }
    ]


def test_get_transformations_resolves_logical_table_against_postgres():
    with patch('core.store.postgres.PostgresExecutor'):
        spark = MagicMock()
        mock_df = spark.read.jdbc.return_value
        mock_df.columns = [
            'src_app_cd',
            'dataclass',
            'output_col_name',
            'seq',
            'zone',
            'stage',
            'sub_stage',
            'expression',
            'status',
        ]
        mock_df.select.return_value = mock_df
        mock_df.filter.return_value = mock_df
        mock_df.orderBy.return_value = mock_df

        row = MagicMock()
        row.asDict.return_value = {
            'SRC_APP_CD': '11392',
            'DATACLASS': 'TRIAL_BALANCE',
            'OUTPUT_COL_NAME': 'DATACLASS',
            'SEQ': 1,
            'ZONE': 'FOUNDRY',
            'STAGE': 'STAGING',
            'SUB_STAGE': None,
            'EXPRESSION': "'TRIAL_BALANCE'",
            'STATUS': 'A',
        }
        mock_df.collect.return_value = [row]

        store = PostgresStore(
            spark=spark,
            table_names=POSTGRES_TABLE_LOCATIONS,
        )

        repository = SpecRepository(store)

        rows = repository.get_transformations(
            dataclass='TRIAL_BALANCE',
            zone='FOUNDRY',
            stage='STAGING',
        )

        spark.read.jdbc.assert_called_once_with(
            url=CONFIG.jdbc_url,
            table='spec.transformation',
            properties=CONFIG.jdbc_properties,
        )

        assert rows == [row.asDict.return_value]


def test_get_file_layout_reads_configured_logical_table_from_csv(spark, tmp_path):
    csv_path = tmp_path / 'CFG_FILE_LAYOUT' / 'data.csv'
    _write_file_layout_csv(csv_path)

    store = CsvStore(
        spark=spark,
        table_locations={'CFG_FILE_LAYOUT': csv_path},
    )

    repository = SpecRepository(store)

    layout = repository.get_file_layout(
        src_app_cd='11392',
        dataclass='TRIAL_BALANCE',
    )

    assert layout == FileLayout(
        src_app_cd='11392',
        dataclass='TRIAL_BALANCE',
        fields=(
            FileLayoutField(
                column_name='SRC_ACCOUNT_ID',
                logical_column_name='SRC_ACCOUNT_ID',
                seq=1,
                datatype='STRING',
            ),
            FileLayoutField(
                column_name='SRC_ACCOUNT_NM',
                logical_column_name='SRC_ACCOUNT_NM',
                seq=2,
                datatype='STRING',
            ),
        ),
    )


def test_get_file_layout_raises_when_not_found(spark, tmp_path):
    csv_path = tmp_path / 'CFG_FILE_LAYOUT' / 'data.csv'
    _write_file_layout_csv(csv_path)

    store = CsvStore(
        spark=spark,
        table_locations={'CFG_FILE_LAYOUT': csv_path},
    )

    repository = SpecRepository(store)

    with pytest.raises(KeyError):
        repository.get_file_layout(
            src_app_cd='99999',
            dataclass='UNKNOWN',
        )
