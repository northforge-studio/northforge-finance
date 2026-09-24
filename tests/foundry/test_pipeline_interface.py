from uuid import uuid4

from core.runs.models import RunIdentity, RunStatus, ZoneResult

from tests.support.pipelines import NoOpPipeline, make_pipeline


class _InterfacePipeline(NoOpPipeline):
    '''A minimal BasePipeline subclass that only implements interface.'''

    def __init__(self, interface_df, **kwargs):
        super().__init__(**kwargs)
        self._interface_df = interface_df
        self.post_interface_called_with = None


    def pre_interface(self, workflow_run_id):
        self.pre_interface_called_with = workflow_run_id
        return self._interface_df


    def main_interface(self, df):
        return df


    def post_interface(self, df):
        self.post_interface_called_with = df
        return self._config.business_dt


def test_interface_returns_zone_result_for_supplied_identity(spark):
    df = spark.createDataFrame([(1,), (2,)], schema=['ID'])
    pipeline = make_pipeline(_InterfacePipeline, interface_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    result = pipeline.interface(identity)

    assert isinstance(result, ZoneResult)
    assert result.zone == 'INTERFACE'
    assert result.status == RunStatus.SUCCEEDED
    assert result.record_count == 2
    assert result.identity == identity

    assert pipeline.post_interface_called_with is not None
    assert pipeline.post_interface_called_with.count() == 2


def test_interface_passes_workflow_run_id_to_pre_interface(spark):
    df = spark.createDataFrame([(1,)], schema=['ID'])
    pipeline = make_pipeline(_InterfacePipeline, interface_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.interface(identity)

    assert pipeline.pre_interface_called_with == identity.workflow_run_id


def test_interface_stamps_supplied_workflow_and_producer_run_id(spark):
    df = spark.createDataFrame([(1,)], schema=['ID'])
    pipeline = make_pipeline(_InterfacePipeline, interface_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.interface(identity)

    row = pipeline.post_interface_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)
