from uuid import uuid4

from core.runs.models import RunIdentity, RunStatus, ZoneResult

from tests.support.pipelines import NoOpPipeline, make_pipeline


class _StagingPipeline(NoOpPipeline):
    '''A minimal BasePipeline subclass that only implements staging.'''

    def __init__(self, staging_df, **kwargs):
        super().__init__(**kwargs)
        self._staging_df = staging_df
        self.post_staging_called_with = None


    def pre_staging(self):
        return self._staging_df


    def main_staging(self, df):
        return df


    def post_staging(self, df):
        self.post_staging_called_with = df
        return self._config.business_dt


def test_staging_returns_zone_result_for_supplied_identity(spark):
    df = spark.createDataFrame([(1,), (2,), (3,)], ['ID'])
    pipeline = make_pipeline(_StagingPipeline, staging_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    result = pipeline.staging(identity)

    assert isinstance(result, ZoneResult)
    assert result.zone == 'STAGING'
    assert result.status == RunStatus.SUCCEEDED
    assert result.record_count == 3
    assert result.identity == identity

    assert pipeline.post_staging_called_with is not None
    assert pipeline.post_staging_called_with.count() == 3


def test_staging_stamps_supplied_workflow_and_producer_run_id(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = make_pipeline(_StagingPipeline, staging_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=None,
    )

    pipeline.staging(identity)

    row = pipeline.post_staging_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)


def test_staging_overwrites_any_preexisting_run_identity_columns(spark):
    upstream_workflow_run_id = str(uuid4())
    upstream_producer_run_id = str(uuid4())

    df = spark.createDataFrame(
        [(1, upstream_workflow_run_id, upstream_producer_run_id)],
        ['ID', 'WORKFLOW_RUN_ID', 'PRODUCER_RUN_ID'],
    )
    pipeline = make_pipeline(_StagingPipeline, staging_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=None,
    )

    pipeline.staging(identity)

    row = pipeline.post_staging_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)
    assert row['PRODUCER_RUN_ID'] != upstream_producer_run_id
