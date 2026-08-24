from unittest.mock import MagicMock, patch

from core.db import PostgresConfig
from core.store import CsvStore, PostgresStore
from foundry.repository import TransformationRepository


CONFIG = PostgresConfig(
    host='localhost',
    port=5432,
    database='northforge_finance',
    user='leo',
    password='northforge',
)

POSTGRES_TABLE_LOCATIONS = {
    'CFG_TRANSFORMATIONS': 'foundry_config.transformation',
}


def _write_transformations_csv(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(
            'DATACLASS,ZONE,STAGE,SUB_STAGE,STATUS,SEQ\n'
            'TRIAL_BALANCE,FOUNDRY,STAGING,,A,1\n'
        )


def test_get_transformations_reads_configured_logical_table_from_csv(spark, tmp_path):
    csv_path = tmp_path / 'CFG_TRANSFORMATIONS' / 'data.csv'
    _write_transformations_csv(csv_path)

    store = CsvStore(
        spark=spark,
        table_locations={'CFG_TRANSFORMATIONS': csv_path},
    )

    repository = TransformationRepository(store)

    rows = repository.get_transformations(
        dataclass='TRIAL_BALANCE',
        zone='FOUNDRY',
        stage='STAGING',
    )

    assert rows == [
        {
            'DATACLASS': 'TRIAL_BALANCE',
            'ZONE': 'FOUNDRY',
            'STAGE': 'STAGING',
            'SUB_STAGE': None,
            'STATUS': 'A',
            'SEQ': 1,
        }
    ]


def test_get_transformations_resolves_logical_table_against_postgres():
    with patch('core.store.postgres.PostgresExecutor'):
        spark = MagicMock()
        mock_df = spark.read.jdbc.return_value
        mock_df.filter.return_value = mock_df
        mock_df.orderBy.return_value = mock_df

        row = MagicMock()
        row.asDict.return_value = {
            'DATACLASS': 'TRIAL_BALANCE',
            'ZONE': 'FOUNDRY',
            'STAGE': 'STAGING',
            'SUB_STAGE': None,
            'STATUS': 'A',
            'SEQ': 1,
        }
        mock_df.collect.return_value = [row]

        store = PostgresStore(
            spark=spark,
            table_names=POSTGRES_TABLE_LOCATIONS,
        )

        repository = TransformationRepository(store)

        rows = repository.get_transformations(
            dataclass='TRIAL_BALANCE',
            zone='FOUNDRY',
            stage='STAGING',
        )

        spark.read.jdbc.assert_called_once_with(
            url=CONFIG.jdbc_url,
            table='foundry_config.transformation',
            properties=CONFIG.jdbc_properties,
        )

        assert rows == [row.asDict.return_value]
