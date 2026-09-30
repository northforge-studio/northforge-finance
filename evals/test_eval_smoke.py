from break_analysis.model_provider import OllamaChatModelProvider
from evals.runner import EvalRunner
from evals.scenarios.atlas import atlas_unresolved_account
from evals.scenarios.many_to_one import many_to_one_mixed_findings
from evals.scenarios.mixed import mixed_registry_and_atlas
from evals.scenarios.registry import (
    registry_inactive_account,
    registry_missing_account,
)
from evals.scenarios.unexplained import interface_only_no_supported_cause


def test_registry_inactive_account(model_provider):
    scenario = registry_inactive_account()

    runner = EvalRunner(model_provider)
    result = runner.run(scenario)

    print(result)


def test_registry_missing_account(model_provider):
    scenario = registry_missing_account()

    runner = EvalRunner(model_provider)
    result = runner.run(scenario)

    print(result)


def test_atlas_unresolved_account(model_provider):
    scenario = atlas_unresolved_account()

    runner = EvalRunner(model_provider)
    result = runner.run(scenario)

    print(result)


def test_mixed_registry_and_atlas(model_provider):
    scenario = mixed_registry_and_atlas()

    runner = EvalRunner(model_provider)
    result = runner.run(scenario)

    print(result)


def test_interface_only_no_supported_cause(model_provider):
    scenario = interface_only_no_supported_cause()

    runner = EvalRunner(model_provider)
    result = runner.run(scenario)

    print(result)


def test_many_to_one_mixed_findings(model_provider):
    scenario = many_to_one_mixed_findings()

    runner = EvalRunner(model_provider)
    result = runner.run(scenario)

    print(result)


if __name__ == '__main__':
    # model_provider = OllamaChatModelProvider(
    #     model='qwen3:8b',
    #     temperature=0
    # )

    model_provider = OllamaChatModelProvider(model='qwen3:14b-q4_K_M', temperature=0)

    # test_registry_inactive_account(model_provider)
    # test_registry_missing_account(model_provider)
    # test_atlas_unresolved_account(model_provider)
    # test_mixed_registry_and_atlas(model_provider)
    # test_interface_only_no_supported_cause(model_provider)
    test_many_to_one_mixed_findings(model_provider)
