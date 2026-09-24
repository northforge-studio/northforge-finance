from langchain_ollama import ChatOllama

from evals.runner import EvalRunner
from evals.scenarios.registry import registry_inactive_account


def test_registry_inactive_account(llm):
    scenario = registry_inactive_account()

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

    test_registry_inactive_account(llm)
