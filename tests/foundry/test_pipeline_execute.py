from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from core.runs import RunTracker, RunStatus, PipelineResult, RunIdentity, WorkflowRun
from foundry.pipeline.base import BasePipeline
from foundry.models import PipelineConfig


class _StubPipeline(BasePipeline):
    """A minimal BasePipeline subclass that overrides run() directly,
    isolating execute()'s workflow-lifecycle behavior from zone logic."""

    def __init__(self, raise_error=False, **kwargs):
        super().__init__(**kwargs)
        self._raise_error = raise_error
        self.run_called_with = None


    def run(self, workflow_run_id):
        self.run_called_with = workflow_run_id

        if self._raise_error:
            raise ValueError('boom')

        return PipelineResult(
            identity=RunIdentity(
                workflow_run_id=workflow_run_id,
                run_id=uuid4(),
                parent_run_id=None,
            ),
            status=RunStatus.SUCCEEDED,
            zones=(),
        )


    def pre_staging(self): ...
    def main_staging(self, df): ...
    def post_staging(self, df): ...
    def pre_enrichment(self): ...
    def main_enrichment(self, df): ...
    def post_enrichment(self, df): ...
    def pre_reporting(self): ...
    def main_reporting(self, df): ...
    def post_reporting(self, df): ...
    def pre_posting(self): ...
    def main_posting(self, df): ...
    def post_posting(self, df): ...
    def pre_interface(self): ...
    def main_interface(self, df): ...
    def post_interface(self, df): ...


def _make_workflow_run(**overrides):
    defaults = dict(
        workflow_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        batch_id='1',
        status=RunStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
    )
    defaults.update(overrides)
    return WorkflowRun(**defaults)


def _make_pipeline(run_tracker, raise_error=False):
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        batch_id='1',
    )
    return _StubPipeline(
        raise_error=raise_error,
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
        run_tracker=run_tracker,
    )


def test_execute_starts_workflow_from_pipeline_config():
    run_tracker = MagicMock(spec=RunTracker)
    workflow = _make_workflow_run()
    run_tracker.start_workflow.return_value = workflow

    pipeline = _make_pipeline(run_tracker=run_tracker)

    pipeline.execute()

    run_tracker.start_workflow.assert_called_once_with(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
        batch_id='1',
    )


def test_execute_passes_workflow_run_id_into_run():
    run_tracker = MagicMock(spec=RunTracker)
    workflow = _make_workflow_run()
    run_tracker.start_workflow.return_value = workflow

    pipeline = _make_pipeline(run_tracker=run_tracker)

    pipeline.execute()

    assert pipeline.run_called_with == workflow.workflow_run_id


def test_execute_completes_workflow_and_returns_pipeline_result_on_success():
    run_tracker = MagicMock(spec=RunTracker)
    workflow = _make_workflow_run()
    run_tracker.start_workflow.return_value = workflow

    pipeline = _make_pipeline(run_tracker=run_tracker)

    result = pipeline.execute()

    assert isinstance(result, PipelineResult)
    assert result.identity.workflow_run_id == workflow.workflow_run_id

    run_tracker.complete_workflow.assert_called_once_with(workflow.workflow_run_id)
    run_tracker.fail_workflow.assert_not_called()


def test_execute_fails_workflow_and_reraises_on_error():
    run_tracker = MagicMock(spec=RunTracker)
    workflow = _make_workflow_run()
    run_tracker.start_workflow.return_value = workflow

    pipeline = _make_pipeline(run_tracker=run_tracker, raise_error=True)

    with pytest.raises(ValueError, match='boom'):
        pipeline.execute()

    run_tracker.fail_workflow.assert_called_once_with(workflow.workflow_run_id)
    run_tracker.complete_workflow.assert_not_called()
