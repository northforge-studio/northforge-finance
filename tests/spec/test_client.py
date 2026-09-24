import pytest

from spec import SpecClient

from tests.support.paths import SPEC_TRANSFORMATION_PATH, SPEC_FILE_LAYOUT_PATH


@pytest.fixture(scope='module')
def spec(spark):
    return SpecClient.from_csv(
        spark=spark,
        transformation_path=SPEC_TRANSFORMATION_PATH,
        file_layout_path=SPEC_FILE_LAYOUT_PATH,
    )


def test_apply_transformation_adds_configured_output_column(spark, spec):
    # STG/PRE for TRIAL_BALANCE also configures NORM_ACCT_SIGN, which
    # reads SRC_ACCT_TYPE -- supply it so that transformation resolves.
    df = spark.createDataFrame([('11392', 'ASSET')], schema=['SRC_APP_CD', 'SRC_ACCT_TYPE'])

    result = spec.apply_transformation(
        df,
        dataclass='TRIAL_BALANCE',
        zone='STG',
        stage='PRE',
    )

    assert result.first()['DATACLASS'] == 'TRIAL_BALANCE'
