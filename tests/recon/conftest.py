import pytest

from tests.support.constants import BUSINESS_DT


@pytest.fixture
def workflow(run_tracker):
    return run_tracker.start_workflow(dataclass='TRIAL_BALANCE', business_dt=BUSINESS_DT)
