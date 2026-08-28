from datetime import date
from unittest.mock import MagicMock

import pytest

from foundry.pipeline.base import BasePipeline
from foundry.pipeline.trial_balance import TrialBalancePipeline
from foundry.models import PipelineConfig


class _NoOpPipeline(BasePipeline):
    def pre_staging(self): ...
    def main_staging(self, df): ...
    def post_staging(self, df): ...
    def pre_enrichment(self, workflow_run_id): ...
    def main_enrichment(self, df): ...
    def post_enrichment(self, df): ...
    def pre_reporting(self, workflow_run_id): ...
    def main_reporting(self, df): ...
    def post_reporting(self, df): ...
    def pre_posting(self, workflow_run_id): ...
    def main_posting(self, df): ...
    def post_posting(self, df): ...
    def pre_interface(self, workflow_run_id): ...
    def main_interface(self, df): ...
    def post_interface(self, df): ...


def test_base_pipeline_no_longer_accepts_a_run_tracker():
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
    )

    with pytest.raises(TypeError):
        _NoOpPipeline(
            config=config,
            atlas=MagicMock(),
            reference=MagicMock(),
            spec=MagicMock(),
            run_tracker=MagicMock(),
        )


def test_trial_balance_pipeline_no_longer_accepts_a_run_tracker():
    with pytest.raises(TypeError):
        TrialBalancePipeline(
            business_dt=date(2026, 8, 24),
            atlas=MagicMock(),
            repository=MagicMock(),
            reference=MagicMock(),
            spec=MagicMock(),
            run_tracker=MagicMock(),
        )


def test_base_pipeline_default_rollback_execution_is_a_no_op():
    config = PipelineConfig(
        dataclass='TRIAL_BALANCE',
        business_dt=date(2026, 8, 24),
    )
    pipeline = _NoOpPipeline(
        config=config,
        atlas=MagicMock(),
        reference=MagicMock(),
        spec=MagicMock(),
    )

    # Should not raise, and should not touch any collaborator.
    pipeline.rollback_execution('STAGING', MagicMock())
