from unittest.mock import MagicMock

import pytest

from foundry.pipeline.trial_balance import TrialBalancePipeline

from tests.support.constants import BUSINESS_DT
from tests.support.pipelines import make_pipeline


def test_base_pipeline_no_longer_accepts_a_run_tracker():
    with pytest.raises(TypeError):
        make_pipeline(run_tracker=MagicMock())


def test_trial_balance_pipeline_no_longer_accepts_a_run_tracker():
    with pytest.raises(TypeError):
        TrialBalancePipeline(
            business_dt=BUSINESS_DT,
            atlas=MagicMock(),
            repository=MagicMock(),
            reference=MagicMock(),
            spec=MagicMock(),
            run_tracker=MagicMock(),
        )


def test_base_pipeline_default_rollback_execution_is_a_no_op():
    pipeline = make_pipeline()

    # Should not raise, and should not touch any collaborator.
    pipeline.rollback_execution('STAGING', MagicMock())
