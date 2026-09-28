import time

from langchain_ollama import ChatOllama

from evals.runner import EvalRunner
from evals.scenarios import v1_scenarios


def main():
    llm = ChatOllama(
        model='qwen3:14b-q4_K_M',
        temperature=0,
    )

    runner = EvalRunner(llm)
    scenarios = v1_scenarios()
    total = len(scenarios)

    print()
    print('V1 Break Analysis Eval Suite')
    print('-' * 60)

    passed = 0
    suite_start = time.monotonic()

    for index, scenario in enumerate(scenarios, start=1):
        print()
        print(f'[{index}/{total}] {scenario.name}', flush=True)

        start = time.monotonic()
        result = runner.run(scenario)
        duration = time.monotonic() - start

        outcome = 'PASS' if result.grade.passed else 'FAIL'

        print(f'      {outcome}  {duration:>7.1f}s', flush=True)

        for failure in result.grade.failures:
            print(f'      - {failure}', flush=True)

        passed += result.grade.passed

    suite_duration = time.monotonic() - suite_start

    print()
    print('-' * 60)
    print(f'Passed: {passed}/{total}')
    print(f'Failed: {total - passed}/{total}')
    print(f'Total: {suite_duration:.1f}s')


if __name__ == '__main__':
    main()
