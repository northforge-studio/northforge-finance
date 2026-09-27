from langchain_ollama import ChatOllama

from evals.runner import EvalRunner
from evals.scenarios import v1_scenarios


def main():
    llm = ChatOllama(
        model='qwen3:14b-q4_K_M',
        temperature=0,
    )

    runner = EvalRunner(llm)

    results = [
        runner.run(scenario)
        for scenario in v1_scenarios()
    ]

    print()
    print('V1 Break Analysis Eval Suite')
    print('-' * 80)

    for result in results:
        outcome = 'PASS' if result.grade.passed else 'FAIL'

        print(
            f'{result.scenario_name:<40} {outcome}'
        )

        for failure in result.grade.failures:
            print(f'  - {failure}')

    passed = sum(result.grade.passed for result in results)

    print('-' * 80)
    print(f'{passed}/{len(results)} scenarios passed')


if __name__ == '__main__':
    main()