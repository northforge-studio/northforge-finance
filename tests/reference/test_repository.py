import pytest

from reference.repository import CsvRepository, Repository
from core.store import CsvStore


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_paths={
            'REF_FX_RATE': 'data/reference/fx_rate.csv',
            'REF_COUNTERPARTY': 'data/reference/counterparty.csv',
        },
    )
    return CsvRepository(store)


def test_get_fx_rate_reads_configured_columns(repository):
    df = repository.get_fx_rate()

    assert df.columns == [
        'AUD_LOAD_ID',
        'CONVERSION_DT',
        'VER_NB',
        'FROM_CURRENCY',
        'TO_CURRENCY',
        'FX_RATE',
    ]
    assert df.count() > 0


def test_get_counterparty_reads_configured_columns(repository):
    df = repository.get_counterparty()

    assert df.columns == [
        'AUD_LOAD_ID',
        'BUSINESS_DT',
        'VER_NB',
        'CPTY_REF_ID',
        'CLIENT_ID',
        'CPTY_NM',
        'CLIENT_ID_TYPE',
    ]
    assert df.count() > 0


def test_csv_repository_satisfies_protocol(spark):
    repository: Repository = CsvRepository(
        CsvStore(
            spark=spark,
            table_paths={
                'REF_FX_RATE': 'data/reference/fx_rate.csv',
                'REF_COUNTERPARTY': 'data/reference/counterparty.csv',
            },
        )
    )

    assert repository.get_fx_rate().count() > 0
