import pytest

from spec import SpecClient


@pytest.fixture(scope='module')
def spec(spark):
    return SpecClient.from_csv(
        spark=spark,
        transformation_path='data/spec/transformation.csv',
        file_layout_path='data/spec/file_layout.csv',
    )


def test_apply_transformation_adds_configured_output_column(spark, spec):
    # STG/PRE for TRIAL_BALANCE also configures NORM_ACCT_SIGN, which
    # reads SRC_ACCT_TYPE -- supply it so that transformation resolves.
    df = spark.createDataFrame([('11392', 'ASSET')], ['SRC_APP_CD', 'SRC_ACCT_TYPE'])

    result = spec.apply_transformation(
        df,
        dataclass='TRIAL_BALANCE',
        zone='STG',
        stage='PRE',
    )

    assert result.first()['DATACLASS'] == 'TRIAL_BALANCE'
