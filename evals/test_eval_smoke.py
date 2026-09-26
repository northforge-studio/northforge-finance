from langchain_ollama import ChatOllama

from evals.runner import EvalRunner
from evals.scenarios.registry import (
    registry_inactive_account,
    registry_missing_account,
)
from evals.scenarios.atlas import atlas_unresolved_account
from evals.scenarios.mixed import mixed_registry_and_atlas
from evals.scenarios.unexplained import interface_only_no_supported_cause
from evals.scenarios.many_to_one import many_to_one_mixed_findings


def test_registry_inactive_account(llm):
    scenario = registry_inactive_account()

    runner = EvalRunner(llm)
    result = runner.run(scenario)
    
    print(result)


def test_registry_missing_account(llm):
    scenario = registry_missing_account()

    runner = EvalRunner(llm)
    result = runner.run(scenario)

    print(result)


def test_atlas_unresolved_account(llm):
    scenario = atlas_unresolved_account()

    runner = EvalRunner(llm)
    result = runner.run(scenario)

    print(result)


def test_mixed_registry_and_atlas(llm):
    scenario = mixed_registry_and_atlas()

    runner = EvalRunner(llm)
    result = runner.run(scenario)

    print(result)


def test_interface_only_no_supported_cause(llm):
    scenario = interface_only_no_supported_cause()

    runner = EvalRunner(llm)
    result = runner.run(scenario)

    print(result)


def test_many_to_one_mixed_findings(llm):
    scenario = many_to_one_mixed_findings()

    runner = EvalRunner(llm)
    result = runner.run(scenario)

    print(result)



if __name__ == "__main__":

    # llm = ChatOllama(
    #     model='qwen3:8b',
    #     temperature=0
    # )

    llm = ChatOllama(
        model='qwen3:14b-q4_K_M',
        temperature=0
    )

    # test_registry_inactive_account(llm)
    # test_registry_missing_account(llm)
    # test_atlas_unresolved_account(llm)
    # test_mixed_registry_and_atlas(llm)
    # test_interface_only_no_supported_cause(llm)
    test_many_to_one_mixed_findings(llm)
