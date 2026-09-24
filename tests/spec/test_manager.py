from spec.manager import SpecManager


class _FakeRepository:
    '''Duck-types SpecRepository.get_transformations, and records each call.'''

    def __init__(self, transformations):
        self._transformations = transformations
        self.calls = []


    def get_transformations(self, dataclass, zone, stage, sub_stage=''):
        self.calls.append(
            (dataclass, zone, stage, sub_stage)
        )
        return self._transformations


def test_apply_adds_configured_output_column(spark):
    repository = _FakeRepository([
        {'OUTPUT_COL_NAME': 'DATACLASS', 'EXPRESSION': "'TRIAL_BALANCE'"},
    ])
    manager = SpecManager(repository)

    df = spark.createDataFrame([(1,)], schema=['ID'])
    result = manager.apply_transformation(
        df,
        dataclass='TRIAL_BALANCE',
        zone='STG',
        stage='PRE',
    )

    assert result.first()['DATACLASS'] == 'TRIAL_BALANCE'
    assert repository.calls == [('TRIAL_BALANCE', 'STG', 'PRE', '')]


def test_apply_chains_multiple_transformations_in_order(spark):
    repository = _FakeRepository([
        {'OUTPUT_COL_NAME': 'A', 'EXPRESSION': '1'},
        {'OUTPUT_COL_NAME': 'B', 'EXPRESSION': 'A + 1'},
    ])
    manager = SpecManager(repository)

    df = spark.createDataFrame([(1,)], schema=['ID'])
    result = manager.apply_transformation(
        df,
        dataclass='X',
        zone='Y',
        stage='Z',
    )

    row = result.first()
    assert row['A'] == 1
    assert row['B'] == 2


def test_apply_with_no_transformations_returns_dataframe_unchanged(spark):
    repository = _FakeRepository([])
    manager = SpecManager(repository)

    df = spark.createDataFrame([(1,)], schema=['ID'])
    result = manager.apply_transformation(
        df,
        dataclass='X',
        zone='Y',
        stage='Z',
    )

    assert result.columns == ['ID']


def test_apply_passes_sub_stage_through_to_repository(spark):
    repository = _FakeRepository([])
    manager = SpecManager(repository)

    df = spark.createDataFrame([(1,)], schema=['ID'])
    manager.apply_transformation(
        df,
        dataclass='X',
        zone='Y',
        stage='Z',
        sub_stage='PRE_COA',
    )

    assert repository.calls == [('X', 'Y', 'Z', 'PRE_COA')]
