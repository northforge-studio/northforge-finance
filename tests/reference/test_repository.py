import pytest

from core.store import CsvStore

from reference import ReferenceData
from reference.repository import ReferenceRepository


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            'REF_FX_RATE': 'data/reference/fx_rate.csv',
            'REF_COUNTERPARTY': 'data/reference/counterparty.csv',
        },
    )
    return ReferenceRepository(store)


def test_get_fx_rate_reads_configured_columns(repository):
    df = repository.get_reference_data(ReferenceData.FX_RATE)

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
    df = repository.get_reference_data(ReferenceData.COUNTERPARTY)

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


class _FakeStore:
    """A minimal Store stand-in, to prove ReferenceRepository is backend-agnostic."""

    def __init__(self, tables):
        self._tables = tables

    def read(self, table_name, schema=None):
        return self._tables[table_name]


def test_get_fx_rate_works_against_a_fake_store(spark):
    fx_rate_df = spark.createDataFrame(
        [('CAD', 'USD', 1.35)],
        ['FROM_CURRENCY', 'TO_CURRENCY', 'FX_RATE'],
    )

    store = _FakeStore({'REF_FX_RATE': fx_rate_df})
    repository = ReferenceRepository(store)

    df = repository.get_reference_data(ReferenceData.FX_RATE)

    assert df.count() == 1
    assert df.first()['FX_RATE'] == 1.35
