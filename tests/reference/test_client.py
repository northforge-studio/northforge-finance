import pytest

from reference import ReferenceClient
from reference.models import ReferenceData

from tests.support.paths import REFERENCE_FX_RATE_PATH, REFERENCE_COUNTERPARTY_PATH


@pytest.fixture(scope='module')
def reference(spark):
    return ReferenceClient.from_csv(
        spark=spark,
        fx_rate_path=REFERENCE_FX_RATE_PATH,
        counterparty_path=REFERENCE_COUNTERPARTY_PATH,
    )


def test_enrich_fx_rate_joins_on_currency_pair(spark, reference):
    df = spark.createDataFrame(
        [
            ('record-1', 'CAD', 'USD'),
        ],
        schema=[
            'RECORD_ID',
            'POSTING_MEASURE_CCY_CD',
            'POSTING_MEASURE_FUNC_CCY_CD',
        ],
    )

    result = reference.enrich_reference_data(df, ReferenceData.FX_RATE)

    rows = result.collect()

    assert len(rows) == 1
    assert 'FX_RATE' in result.columns
    assert rows[0]['FX_RATE'] is not None


def test_enrich_fx_rate_preserves_unmatched_source_row(spark, reference):
    df = spark.createDataFrame(
        [
            ('record-1', 'XXX', 'YYY'),
        ],
        schema=[
            'RECORD_ID',
            'POSTING_MEASURE_CCY_CD',
            'POSTING_MEASURE_FUNC_CCY_CD',
        ],
    )

    result = reference.enrich_reference_data(df, ReferenceData.FX_RATE)

    rows = result.collect()
    assert len(rows) == 1
    assert rows[0]['FX_RATE'] is None


def test_enrich_counterparty_joins_on_cpty_ref_id(spark, reference):
    df = spark.createDataFrame(
        [
            ('record-1', 'CP-EXT-001'),
        ],
        schema=[
            'RECORD_ID',
            'CPTY_REF_ID',
        ],
    )

    result = reference.enrich_reference_data(df, ReferenceData.COUNTERPARTY)

    rows = result.collect()
    assert len(rows) == 1
    assert rows[0]['CLIENT_ID_TYPE'] == 'THIRDPARTY'


def test_enrich_counterparty_preserves_unmatched_source_row(spark, reference):
    df = spark.createDataFrame(
        [
            ('record-1', 'unknown-cpty'),
        ],
        schema=[
            'RECORD_ID',
            'CPTY_REF_ID',
        ],
    )

    result = reference.enrich_reference_data(df, ReferenceData.COUNTERPARTY)

    rows = result.collect()
    assert len(rows) == 1
    assert rows[0]['CLIENT_ID_TYPE'] is None
