from uuid import uuid4

from core.runs.models import RunIdentity, RunStatus, ZoneResult

from tests.support.pipelines import NoOpPipeline, make_pipeline


class _EnrichmentPipeline(NoOpPipeline):
    '''A minimal BasePipeline subclass that only implements enrichment.'''

    def __init__(self, enrichment_df, **kwargs):
        super().__init__(**kwargs)
        self._enrichment_df = enrichment_df
        self.post_enrichment_called_with = None


    def pre_enrichment(self, workflow_run_id):
        self.pre_enrichment_called_with = workflow_run_id
        return self._enrichment_df


    def main_enrichment(self, df):
        return df


    def post_enrichment(self, df):
        self.post_enrichment_called_with = df
        return self._config.business_dt


def test_enrichment_returns_zone_result_for_supplied_identity(spark):
    df = spark.createDataFrame([(1,), (2,), (3,)], schema=['ID'])
    pipeline = make_pipeline(_EnrichmentPipeline, enrichment_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    result = pipeline.enrichment(identity)

    assert isinstance(result, ZoneResult)
    assert result.zone == 'ENRICHMENT'
    assert result.status == RunStatus.SUCCEEDED
    assert result.record_count == 3
    assert result.identity == identity

    assert pipeline.post_enrichment_called_with is not None
    assert pipeline.post_enrichment_called_with.count() == 3


def test_enrichment_passes_workflow_run_id_to_pre_enrichment(spark):
    df = spark.createDataFrame([(1,)], schema=['ID'])
    pipeline = make_pipeline(_EnrichmentPipeline, enrichment_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.enrichment(identity)

    assert pipeline.pre_enrichment_called_with == identity.workflow_run_id


def test_enrichment_stamps_supplied_workflow_and_producer_run_id(spark):
    df = spark.createDataFrame([(1,)], schema=['ID'])
    pipeline = make_pipeline(_EnrichmentPipeline, enrichment_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.enrichment(identity)

    row = pipeline.post_enrichment_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)


def test_enrichment_overwrites_upstream_producer_run_id(spark):
    upstream_workflow_run_id = str(uuid4())
    upstream_producer_run_id = str(uuid4())

    df = spark.createDataFrame(
        [(1, upstream_workflow_run_id, upstream_producer_run_id)],
        schema=['ID', 'WORKFLOW_RUN_ID', 'PRODUCER_RUN_ID'],
    )
    pipeline = make_pipeline(_EnrichmentPipeline, enrichment_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.enrichment(identity)

    row = pipeline.post_enrichment_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)
    assert row['PRODUCER_RUN_ID'] != upstream_producer_run_id
