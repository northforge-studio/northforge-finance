from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

from core.runs import RunIdentity, RunStatus, ZoneResult
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


class _PostingPipeline(BasePipeline):
    """A minimal BasePipeline subclass that only implements posting."""

    def __init__(self, posting_df, **kwargs):
        super().__init__(**kwargs)
        self._posting_df = posting_df
        self.post_posting_called_with = None


    def pre_staging(self): ...
    def main_staging(self, df): ...
    def post_staging(self, df): ...
    def pre_enrichment(self, workflow_run_id): ...
    def main_enrichment(self, df): ...
    def post_enrichment(self, df): ...
    def pre_reporting(self, workflow_run_id): ...
    def main_reporting(self, df): ...
    def post_reporting(self, df): ...


    def pre_posting(self, workflow_run_id):
        self.pre_posting_called_with = workflow_run_id
        return self._posting_df


    def main_posting(self, df):
        return df


    def post_posting(self, df):
        self.post_posting_called_with = df
        return self._config.business_dt


    def pre_interface(self, workflow_run_id): ...
    def main_interface(self, df): ...
    def post_interface(self, df): ...


def _make_pipeline(posting_df):
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
    )
    return _PostingPipeline(
        posting_df=posting_df,
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
    )


def test_posting_returns_zone_result_for_supplied_identity(spark):
    df = spark.createDataFrame([(1,), (2,), (3,), (4,)], ['ID'])
    pipeline = _make_pipeline(posting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    result = pipeline.posting(identity)

    assert isinstance(result, ZoneResult)
    assert result.zone == 'POSTING'
    assert result.status == RunStatus.SUCCEEDED
    assert result.record_count == 4
    assert result.identity == identity

    assert pipeline.post_posting_called_with is not None
    assert pipeline.post_posting_called_with.count() == 4


def test_posting_passes_workflow_run_id_to_pre_posting(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(posting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.posting(identity)

    assert pipeline.pre_posting_called_with == identity.workflow_run_id


def test_posting_stamps_supplied_workflow_and_producer_run_id(spark):
    df = spark.createDataFrame([(1,)], ['ID'])
    pipeline = _make_pipeline(posting_df=df)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.posting(identity)

    row = pipeline.post_posting_called_with.collect()[0]
    assert row['WORKFLOW_RUN_ID'] == str(identity.workflow_run_id)
    assert row['PRODUCER_RUN_ID'] == str(identity.run_id)
