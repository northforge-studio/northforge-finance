import pytest

from spec import SpecClient, FileLayout, FileLayoutField


@pytest.fixture(scope='module')
def spec(spark):
    return SpecClient.from_csv(
        spark=spark,
        transformation_path='data/foundry/config/transformations.csv',
        file_layout_path='data/foundry/config/file_layout.csv',
    )


def test_apply_transformations_adds_configured_output_column(spark, spec):
    df = spark.createDataFrame([('11392',)], ['SRC_APP_CD'])

    result = spec.apply_transformations(
        df,
        dataclass='TRIAL_BALANCE',
        zone='STG',
        stage='PRE',
    )

    assert result.first()['DATACLASS'] == 'TRIAL_BALANCE'


def test_get_file_layout_returns_ordered_fields(spec):
    layout = spec.get_file_layout(
        src_app_cd='11392',
        dataclass='TRIAL_BALANCE',
    )

    assert isinstance(layout, FileLayout)
    assert layout.src_app_cd == '11392'
    assert layout.dataclass == 'TRIAL_BALANCE'
    assert layout.fields[0] == FileLayoutField(
        column_name='BATCH_ID',
        logical_column_name='BATCH_ID',
        seq=1,
        datatype='INTEGER',
    )
    assert [field.seq for field in layout.fields] == sorted(
        field.seq for field in layout.fields
    )


def test_get_file_layout_raises_for_unknown_dataclass(spec):
    with pytest.raises(KeyError):
        spec.get_file_layout(
            src_app_cd='11392',
            dataclass='UNKNOWN',
        )
