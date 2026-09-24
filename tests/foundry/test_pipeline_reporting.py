from uuid import uuid4

from core.runs.models import RunIdentity, RunStatus, ZoneResult

from tests.support.pipelines import NoOpPipeline, make_pipeline


class _ReportingPipeline(NoOpPipeline):
    '''A minimal BasePipeline subclass that only implements reporting.'''

    def __init__(self, reporting_df, **kwargs):
        super().__init__(**kwargs)
        self._reporting_df = reporting_df
        self.post_reporting_called_with = None


    def pre_reporting(self, workflow_run_id):
        self.pre_reporting_called_with = workflow_run_id
        return self._reporting_df


    def main_reporting(self, df):
        return df


    def post_reporting(self, df):
        self.post_reporting_called_with = df
        return self._config.business_dt


def test_reporting_returns_zone_result_for_supplied_identity(spark):
    df = spark.createDataFrame([(1,), (2,), (3,)], ['ID'])
    pipeline = make_pipeline(_ReportingPipeline, reporting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    result = pipeline.reporting(identity)

    assert isinstance(result, ZoneResult)
    assert result.zone == 'REPORTING'
    assert result.status == RunStatus.SUCCEEDED
    assert result.record_count == 3
    assert result.identity == identity

    assert pipeline.post_reporting_called_with is not None
    assert pipeline.post_reporting_called_with.count() == 3


def test_reporting_passes_workflow_run_id_to_pre_reporting(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = make_pipeline(_ReportingPipeline, reporting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.reporting(identity)

    assert pipeline.pre_reporting_called_with == identity.workflow_run_id


def test_reporting_stamps_supplied_workflow_and_producer_run_id(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = make_pipeline(_ReportingPipeline, reporting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.reporting(identity)

    row = pipeline.post_reporting_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)
