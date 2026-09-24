import pytest

from core.store import CsvStore
from reference.models import ReferenceData
from reference.repository import ReferenceRepository

from tests.support.fakes import FakeStore
from tests.support.paths import REFERENCE_FX_RATE_PATH, REFERENCE_COUNTERPARTY_PATH


@pytest.fixture(scope='module')
def repository(spark):
    store = CsvStore(
        spark=spark,
        table_locations={
            'REF_FX_RATE': REFERENCE_FX_RATE_PATH,
            'REF_COUNTERPARTY': REFERENCE_COUNTERPARTY_PATH,
        },
    )
    return ReferenceRepository(store)


def test_get_fx_rate_reads_configured_columns(repository):
    df = repository.get_reference_data(ReferenceData.FX_RATE)

    assert df.columns == [
        'CONVERSION_DT',
        'FROM_CURRENCY',
        'TO_CURRENCY',
        'FX_RATE',
    ]
    assert df.count() > 0


def test_get_counterparty_reads_configured_columns(repository):
    df = repository.get_reference_data(ReferenceData.COUNTERPARTY)

    assert df.columns == [
        'BUSINESS_DT',
        'CPTY_REF_ID',
        'CLIENT_ID',
        'CPTY_NM',
        'CLIENT_ID_TYPE',
    ]
    assert df.count() > 0


def test_get_fx_rate_works_against_a_fake_store(spark):
    fx_rate_df = spark.createDataFrame(
        [('CAD', 'USD', 1.35)],
        schema=['FROM_CURRENCY', 'TO_CURRENCY', 'FX_RATE'],
    )

    store = FakeStore({'REF_FX_RATE': fx_rate_df})
    repository = ReferenceRepository(store)

    df = repository.get_reference_data(ReferenceData.FX_RATE)

    rows = df.collect()
    assert len(rows) == 1
    assert rows[0]['FX_RATE'] == 1.35
