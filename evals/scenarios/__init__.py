from evals.scenarios.registry import (
    registry_inactive_account,
    registry_missing_account,
)
from evals.scenarios.atlas import atlas_unresolved_account
from evals.scenarios.mixed import mixed_registry_and_atlas
from evals.scenarios.unexplained import interface_only_no_supported_cause
from evals.scenarios.many_to_one import many_to_one_mixed_findings


def v1_scenarios():
    return (
        registry_inactive_account(),
        registry_missing_account(),
        atlas_unresolved_account(),
        mixed_registry_and_atlas(),
        interface_only_no_supported_cause(),
        many_to_one_mixed_findings(),
    )
