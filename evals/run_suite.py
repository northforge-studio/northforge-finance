import argparse
import time

from langchain_ollama import ChatOllama

from evals.models import ScenarioSummary
from evals.runner import EvalRunner
from evals.scenarios import v1_scenarios


def _positive_int(value: str) -> int:
    number = int(value)

    if number < 1:
        raise argparse.ArgumentTypeError('must be at least 1')

    return number


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Run the V1 Break Analysis eval suite.',
    )
    parser.add_argument(
        '--repetitions',
        type=_positive_int,
        default=1,
        help='number of times to run each scenario (default: 1)',
    )

    return parser.parse_args()


def main():
    args = _parse_args()
    repetitions = args.repetitions

    llm = ChatOllama(
        model='qwen3:14b-q4_K_M',
        temperature=0,
    )

    runner = EvalRunner(llm)
    scenarios = v1_scenarios()
    total = len(scenarios)

    print()
    print('V1 Break Analysis Eval Suite')
    print('-' * 75)

    summaries = []
    suite_start = time.monotonic()

    for index, scenario in enumerate(scenarios, start=1):
        print()
        print(f'[{index}/{total}] {scenario.name}', flush=True)

        passed_runs = 0
        durations = []
        tool_call_counts = []

        for run in range(1, repetitions + 1):
            print(f'      Run {run}/{repetitions} ... ', end='', flush=True)

            start = time.monotonic()
            result = runner.run(scenario)
            duration = time.monotonic() - start

            outcome = 'PASS' if result.grade.passed else 'FAIL'

            print(f'{outcome}  {duration:>7.1f}s', flush=True)

            for failure in result.grade.failures:
                print(f'      - {failure}', flush=True)

            passed_runs += result.grade.passed
            durations.append(duration)
            tool_call_counts.append(len(result.calls))

        summaries.append(
            ScenarioSummary(
                scenario_name=scenario.name,
                passed_runs=passed_runs,
                total_runs=repetitions,
                avg_duration=sum(durations) / repetitions,
                avg_tool_calls=sum(tool_call_counts) / repetitions,
            )
        )

    suite_duration = time.monotonic() - suite_start

    passed_runs = sum(summary.passed_runs for summary in summaries)
    total_runs = sum(summary.total_runs for summary in summaries)

    print()
    print('-' * 75)
    print(f'{"Scenario":<38}{"Pass Rate":>9}{"Avg Time":>12}{"Avg Tool Calls":>16}')

    for summary in summaries:
        pass_rate = f'{summary.passed_runs}/{summary.total_runs}'

        print(
            f'{summary.scenario_name:<38}{pass_rate:>9}'
            f'{summary.avg_duration:>11.1f}s{summary.avg_tool_calls:>16.1f}'
        )

    print('-' * 75)
    print(f'Overall: {passed_runs}/{total_runs} runs passed')
    print(f'Failed: {total_runs - passed_runs}/{total_runs} runs')
    print(f'Total runtime: {suite_duration:.1f}s')


if __name__ == '__main__':
    main()
