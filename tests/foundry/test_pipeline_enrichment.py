from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

from core.runs import RunIdentity, RunStatus, ZoneResult
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


class _EnrichmentPipeline(BasePipeline):
    """A minimal BasePipeline subclass that only implements enrichment."""

    def __init__(self, enrichment_df, **kwargs):
        super().__init__(**kwargs)
        self._enrichment_df = enrichment_df
        self.post_enrichment_called_with = None


    def pre_staging(self): ...
    def main_staging(self, df): ...
    def post_staging(self, df): ...


    def pre_enrichment(self):
        return self._enrichment_df


    def main_enrichment(self, df):
        return df


    def post_enrichment(self, df):
        self.post_enrichment_called_with = df
        return (self._config.business_dt, self._config.batch_id)


    def pre_reporting(self): ...
    def main_reporting(self, df): ...
    def post_reporting(self, df): ...
    def pre_posting(self): ...
    def main_posting(self, df): ...
    def post_posting(self, df): ...
    def pre_interface(self): ...
    def main_interface(self, df): ...
    def post_interface(self, df): ...


def _make_pipeline(enrichment_df):
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        batch_id='1',
    )
    return _EnrichmentPipeline(
        enrichment_df=enrichment_df,
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
    )


def test_enrichment_returns_zone_result_for_supplied_identity(spark):
    df = spark.createDataFrame([(1,), (2,), (3,)], ['ID'])
    pipeline = _make_pipeline(enrichment_df=df)

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


def test_enrichment_stamps_supplied_workflow_and_producer_run_id(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(enrichment_df=df)

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
        ['ID', 'WORKFLOW_RUN_ID', 'PRODUCER_RUN_ID'],
    )
    pipeline = _make_pipeline(enrichment_df=df)

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
