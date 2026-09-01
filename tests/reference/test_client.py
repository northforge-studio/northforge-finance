import pytest

from reference import ReferenceClient
from reference.models import ReferenceData


@pytest.fixture(scope='module')
def reference(spark):
    return ReferenceClient.from_csv(
        spark=spark,
        fx_rate_path='data/reference/fx_rate.csv',
        counterparty_path='data/reference/counterparty.csv',
    )


def test_enrich_fx_rate_joins_on_currency_pair(spark, reference):
    df = spark.createDataFrame(
        [
            ('record-1', 'CAD', 'USD'),
        ],
        [
            'RECORD_ID',
            'POSTING_MEASURE_CCY_CD',
            'POSTING_MEASURE_FUNC_CCY_CD',
        ],
    )

    result = reference.enrich_reference_data(df, ReferenceData.FX_RATE)

    assert result.count() == 1
    assert 'FX_RATE' in result.columns

    row = result.first()
    assert row['FX_RATE'] is not None


def test_enrich_fx_rate_preserves_unmatched_source_row(spark, reference):
    df = spark.createDataFrame(
        [
            ('record-1', 'XXX', 'YYY'),
        ],
        [
            'RECORD_ID',
            'POSTING_MEASURE_CCY_CD',
            'POSTING_MEASURE_FUNC_CCY_CD',
        ],
    )

    result = reference.enrich_reference_data(df, ReferenceData.FX_RATE)

    assert result.count() == 1
    assert result.first()['FX_RATE'] is None


def test_enrich_counterparty_joins_on_cpty_ref_id(spark, reference):
    df = spark.createDataFrame(
        [
            ('record-1', '54361'),
        ],
        [
            'RECORD_ID',
            'CPTY_REF_ID',
        ],
    )

    result = reference.enrich_reference_data(df, ReferenceData.COUNTERPARTY)

    assert result.count() == 1
    assert result.first()['CLIENT_ID_TYPE'] == 'THIRDPARTY'


def test_enrich_counterparty_preserves_unmatched_source_row(spark, reference):
    df = spark.createDataFrame(
        [
            ('record-1', 'unknown-cpty'),
        ],
        [
            'RECORD_ID',
            'CPTY_REF_ID',
        ],
    )

    result = reference.enrich_reference_data(df, ReferenceData.COUNTERPARTY)

    assert result.count() == 1
    assert result.first()['CLIENT_ID_TYPE'] is None
