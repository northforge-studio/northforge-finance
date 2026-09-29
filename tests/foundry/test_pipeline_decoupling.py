from unittest.mock import MagicMock

import pytest

from foundry.pipeline.base import BasePipeline
from foundry.pipeline.trial_balance import TrialBalancePipeline
from tests.support.constants import BUSINESS_DT
from tests.support.pipelines import NoOpPipeline, make_pipeline


def test_base_pipeline_no_longer_accepts_a_run_tracker():
    with pytest.raises(TypeError, match="unexpected keyword argument 'run_tracker'"):
        make_pipeline(run_tracker=MagicMock())


def test_trial_balance_pipeline_no_longer_accepts_a_run_tracker():
    with pytest.raises(TypeError, match="unexpected keyword argument 'run_tracker'"):
        TrialBalancePipeline(
            business_dt=BUSINESS_DT,
            atlas=MagicMock(),
            repository=MagicMock(),
            reference=MagicMock(),
            spec=MagicMock(),
            run_tracker=MagicMock(),  # pyright: ignore[reportCallIssue]
        )


def test_base_pipeline_without_rollback_execution_cannot_instantiate():
    class _PipelineWithoutRollback(NoOpPipeline):
        rollback_execution = BasePipeline.rollback_execution

    with pytest.raises(TypeError, match='rollback_execution'):
        make_pipeline(_PipelineWithoutRollback)
