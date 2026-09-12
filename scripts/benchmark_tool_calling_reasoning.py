"""
Diagnostic-only benchmark: does disabling Qwen3 "thinking" for the
Break Analysis Agent's tool-selection runnable reduce latency/tokens
without changing tool-call correctness?

Compares, per scenario:

  A. current config:   llm.bind_tools(tools)
  B. candidate config:  llm.bind_tools(tools, reasoning=False)

against a hand-defined expected tool-call set, using the real
TOOL_SYSTEM_PROMPT and the actual validate_segment/get_segment_details
tool schemas (built exactly as BreakAnalysisAgent.__init__ builds them).

Does not touch break_analysis/agent.py and does not exercise the
structured-output (finalization) runnable.

Run with the project's own virtualenv (needed because break_analysis.models
transitively imports registry/gl, which import pyspark):

    .venv/bin/python3 -m scripts.benchmark_tool_calling_reasoning
"""

import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Callable
from uuid import uuid4

from langchain_ollama import ChatOllama
from langchain_core.tools import StructuredTool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from break_analysis.models import (
    BreakCase,
    BreakCaseEvidence,
    BreakRecord,
    BreakTopology,
)
from break_analysis.prompts import TOOL_SYSTEM_PROMPT
from break_analysis.tools import RegistryTools, ValidateSegmentInput
from gl.models import GLSegments
from registry.models import GLSegmentType


MODEL = 'qwen3:8b'
TEMPERATURE = 0
REPS = 2
AS_OF_DATE = date(2026, 9, 1)
BUSINESS_DT = AS_OF_DATE.isoformat()


def _segments(**overrides) -> GLSegments:
    defaults = dict(
        entity_cd=None, branch_cd=None, dept_cd=None, gl_account=None,
        sub_account=None, affiliate_cd=None, product_cd=None,
        book_cd=None, source_cd=None,
    )
    defaults.update(overrides)
    return GLSegments(**defaults)


def _record(**overrides) -> BreakRecord:
    defaults = dict(
        recon_result_id=uuid4(),
        workflow_run_id=uuid4(),
        as_of_date=AS_OF_DATE,
        accounted_currency='USD',
        interface_balance=Decimal('1500.00'),
        gl_balance=Decimal('0.00'),
        difference_amount=Decimal('1500.00'),
    )
    defaults.update(overrides)
    return BreakRecord(**defaults)


ToolCall = dict


def normalize(tool_call: ToolCall) -> tuple:
    args = tool_call['args']
    return (tool_call['name'], tuple(sorted(args.items())))


@dataclass
class Scenario:
    name: str
    description: str
    messages: list
    required: list[Callable[[ToolCall], bool]] = field(default_factory=list)
    required_labels: list[str] = field(default_factory=list)
    forbidden: list[Callable[[ToolCall], bool]] = field(default_factory=list)
    forbidden_labels: list[str] = field(default_factory=list)
    expect_no_tool_calls: bool = False


def is_call(name: str, segment_type: str, segment_value: str):
    def predicate(call: ToolCall) -> bool:
        args = call['args']
        return (
            call['name'] == name
            and str(args.get('segment_type')) == segment_type
            and args.get('segment_value') == segment_value
        )
    return predicate


# -- Scenario 1: MANY_TO_ONE, multiple distinct segment values ------------

def scenario_many_to_one() -> Scenario:
    case = BreakCase(
        case_id=uuid4(),
        topology=BreakTopology.MANY_TO_ONE,
        investigation_records=(
            _record(segments=_segments(entity_cd='E1', gl_account='210000')),
            _record(segments=_segments(entity_cd='E1', gl_account='220000')),
        ),
        pivot=_record(
            segments=_segments(entity_cd='E1', gl_account='999999'),
            interface_balance=Decimal('0.00'),
            gl_balance=Decimal('3000.00'),
            difference_amount=Decimal('3000.00'),
        ),
    )
    return Scenario(
        name='many_to_one_multi_segment',
        description=(
            'MANY_TO_ONE case with two investigation records carrying '
            'distinct GL_ACCOUNT values (210000, 220000) rolling up to '
            'one pivot (999999). Expects both distinct values validated; '
            'the pivot value must not be validated.'
        ),
        messages=[HumanMessage(content=str(case))],
        required=[
            is_call('validate_segment', 'GL_ACCOUNT', '210000'),
            is_call('validate_segment', 'GL_ACCOUNT', '220000'),
        ],
        required_labels=[
            'validate_segment(GL_ACCOUNT, 210000)',
            'validate_segment(GL_ACCOUNT, 220000)',
        ],
        forbidden=[
            is_call('validate_segment', 'GL_ACCOUNT', '999999'),
        ],
        forbidden_labels=[
            'validate_segment(GL_ACCOUNT, 999999) [pivot value]',
        ],
    )


# -- Scenario 2: relaxed_segments present ---------------------------------

def scenario_relaxed_segments() -> Scenario:
    case = BreakCase(
        case_id=uuid4(),
        topology=BreakTopology.UNMATCHED,
        investigation_records=(
            _record(segments=_segments(entity_cd='E1', gl_account='555555')),
        ),
        evidence=BreakCaseEvidence(relaxed_segments=(GLSegmentType.ACCOUNT,)),
    )
    return Scenario(
        name='relaxed_segments_present',
        description=(
            'Single-record case with relaxed_segments=(GL_ACCOUNT,). '
            'Expects the relaxed GL_ACCOUNT value (555555) to be '
            'prioritized/validated.'
        ),
        messages=[HumanMessage(content=str(case))],
        required=[
            is_call('validate_segment', 'GL_ACCOUNT', '555555'),
        ],
        required_labels=[
            'validate_segment(GL_ACCOUNT, 555555)',
        ],
    )


# -- Scenario 3: validate_segment -> get_segment_details follow-up -------

def scenario_follow_up_required() -> Scenario:
    case = BreakCase(
        case_id=uuid4(),
        topology=BreakTopology.UNMATCHED,
        investigation_records=(
            _record(segments=_segments(entity_cd='E1', gl_account='210000')),
        ),
    )
    tool_call_1 = {
        'name': 'validate_segment',
        'args': {
            'segment_type': 'GL_ACCOUNT',
            'segment_value': '210000',
            'business_dt': BUSINESS_DT,
        },
        'id': 'call_1',
        'type': 'tool_call',
    }
    return Scenario(
        name='validate_then_details_follow_up',
        description=(
            'validate_segment already returned is_valid=False for '
            'GL_ACCOUNT 210000. Expects a follow-up get_segment_details '
            'call for the same segment/value/date; re-validating the '
            'same segment via validate_segment is forbidden (redundant).'
        ),
        messages=[
            HumanMessage(content=str(case)),
            AIMessage(content='', tool_calls=[tool_call_1]),
            ToolMessage(
                content=(
                    "SegmentValidationResult(segment_type=GLSegmentType.ACCOUNT, "
                    "segment_value='210000', is_valid=False)"
                ),
                tool_call_id='call_1',
            ),
        ],
        required=[
            is_call('get_segment_details', 'GL_ACCOUNT', '210000'),
        ],
        required_labels=[
            'get_segment_details(GL_ACCOUNT, 210000)',
        ],
        forbidden=[
            is_call('validate_segment', 'GL_ACCOUNT', '210000'),
        ],
        forbidden_labels=[
            'validate_segment(GL_ACCOUNT, 210000) [redundant re-validation]',
        ],
    )


# -- Scenario 4: no-further-tools completion round ------------------------

def scenario_completion_round() -> Scenario:
    case = BreakCase(
        case_id=uuid4(),
        topology=BreakTopology.UNMATCHED,
        investigation_records=(
            _record(segments=_segments(entity_cd='E1', gl_account='210000')),
        ),
    )
    tool_call_1 = {
        'name': 'validate_segment',
        'args': {
            'segment_type': 'GL_ACCOUNT',
            'segment_value': '210000',
            'business_dt': BUSINESS_DT,
        },
        'id': 'call_1',
        'type': 'tool_call',
    }
    tool_call_2 = {
        'name': 'get_segment_details',
        'args': {
            'segment_type': 'GL_ACCOUNT',
            'segment_value': '210000',
            'business_dt': BUSINESS_DT,
        },
        'id': 'call_2',
        'type': 'tool_call',
    }
    return Scenario(
        name='no_further_tools_completion',
        description=(
            'validate_segment (invalid) and get_segment_details (does '
            'not exist) results are both already in history. Expects '
            'no further tool calls and a brief non-empty completion.'
        ),
        messages=[
            HumanMessage(content=str(case)),
            AIMessage(content='', tool_calls=[tool_call_1]),
            ToolMessage(
                content=(
                    "SegmentValidationResult(segment_type=GLSegmentType.ACCOUNT, "
                    "segment_value='210000', is_valid=False)"
                ),
                tool_call_id='call_1',
            ),
            AIMessage(content='', tool_calls=[tool_call_2]),
            ToolMessage(
                content=(
                    "SegmentDetailsResult(segment_type=GLSegmentType.ACCOUNT, "
                    "segment_value='210000', exists=False, status=None)"
                ),
                tool_call_id='call_2',
            ),
        ],
        expect_no_tool_calls=True,
    )


@dataclass
class RunResult:
    scenario: str
    config: str
    rep: int
    wall_ms: int
    total_ms: int | None
    eval_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    tool_calls: list
    content: str
    missing_required: list[str]
    forbidden_hit: list[str]
    extra_calls: list[tuple]
    unexpected_tool_calls_when_none_expected: bool


def ns_to_ms(value) -> int | None:
    return None if value is None else round(value / 1_000_000)


def build_tools() -> list:
    registry_tools = RegistryTools(registry_client=None)
    return [
        StructuredTool.from_function(
            func=registry_tools.validate_segment,
            name='validate_segment',
            description=(
                'Validate whether a GL segment value is active '
                'and valid in Registry.'
            ),
            args_schema=ValidateSegmentInput,
        ),
        StructuredTool.from_function(
            func=registry_tools.get_segment_details,
            name='get_segment_details',
            description=(
                'Retrieve the details of a GL segment value from the Registry, '
                'including its existence and status.'
            ),
            args_schema=ValidateSegmentInput,
        ),
    ]


def evaluate(scenario: Scenario, tool_calls: list) -> tuple:
    missing_required = [
        label for predicate, label in zip(scenario.required, scenario.required_labels)
        if not any(predicate(call) for call in tool_calls)
    ]
    forbidden_hit = [
        label for predicate, label in zip(scenario.forbidden, scenario.forbidden_labels)
        if any(predicate(call) for call in tool_calls)
    ]
    matched = set()
    for predicate in scenario.required:
        for call in tool_calls:
            if predicate(call):
                matched.add(normalize(call))
    extra_calls = [
        normalize(call) for call in tool_calls
        if normalize(call) not in matched
    ]
    unexpected_when_none_expected = (
        scenario.expect_no_tool_calls and len(tool_calls) > 0
    )
    return missing_required, forbidden_hit, extra_calls, unexpected_when_none_expected


def run_scenario(llm: ChatOllama, tools: list, scenario: Scenario) -> list[RunResult]:
    results = []
    for config_name, reasoning_kwargs in [
        ('current (default)', {}),
        ('reasoning=False', {'reasoning': False}),
    ]:
        bound = llm.bind_tools(tools, **reasoning_kwargs)
        messages = [SystemMessage(content=TOOL_SYSTEM_PROMPT), *scenario.messages]

        for rep in range(1, REPS + 1):
            start = time.monotonic()
            response = bound.invoke(messages)
            wall_ms = round((time.monotonic() - start) * 1000)

            usage = response.usage_metadata or {}
            rm = response.response_metadata or {}

            missing_required, forbidden_hit, extra_calls, unexpected = evaluate(
                scenario, response.tool_calls
            )

            results.append(RunResult(
                scenario=scenario.name,
                config=config_name,
                rep=rep,
                wall_ms=wall_ms,
                total_ms=ns_to_ms(rm.get('total_duration')),
                eval_ms=ns_to_ms(rm.get('eval_duration')),
                input_tokens=usage.get('input_tokens'),
                output_tokens=usage.get('output_tokens'),
                tool_calls=[normalize(c) for c in response.tool_calls],
                content=response.content,
                missing_required=missing_required,
                forbidden_hit=forbidden_hit,
                extra_calls=extra_calls,
                unexpected_tool_calls_when_none_expected=unexpected,
            ))

    return results


def print_run(result: RunResult) -> None:
    status_bits = []
    if result.missing_required:
        status_bits.append(f"MISSING={result.missing_required}")
    if result.forbidden_hit:
        status_bits.append(f"FORBIDDEN_HIT={result.forbidden_hit}")
    if result.unexpected_tool_calls_when_none_expected:
        status_bits.append("UNEXPECTED_TOOL_CALLS")
    if result.extra_calls:
        status_bits.append(f"extra={result.extra_calls}")
    status = ' '.join(status_bits) if status_bits else 'OK'

    print(
        f"  [{result.config:<18} rep={result.rep}] "
        f"wall_ms={result.wall_ms:>6} eval_ms={str(result.eval_ms):>6} "
        f"in={str(result.input_tokens):>4} out={str(result.output_tokens):>4} "
        f"tool_calls={result.tool_calls} content={result.content!r:.60} "
        f"-> {status}"
    )


def summarize(all_results: list[RunResult]) -> None:
    print('\n=== summary (avg across reps) ===')
    header = (
        f"{'scenario':<32}{'config':<18}{'avg_out':>8}{'avg_eval_ms':>12}"
        f"{'avg_wall_ms':>12}{'correctness':>14}"
    )
    print(header)

    scenarios = list(dict.fromkeys(r.scenario for r in all_results))
    configs = list(dict.fromkeys(r.config for r in all_results))

    for scenario_name in scenarios:
        for config_name in configs:
            rows = [
                r for r in all_results
                if r.scenario == scenario_name and r.config == config_name
            ]
            avg_out = round(sum(r.output_tokens or 0 for r in rows) / len(rows))
            avg_eval = round(sum(r.eval_ms or 0 for r in rows) / len(rows))
            avg_wall = round(sum(r.wall_ms or 0 for r in rows) / len(rows))
            all_ok = all(
                not r.missing_required
                and not r.forbidden_hit
                and not r.unexpected_tool_calls_when_none_expected
                for r in rows
            )
            correctness = 'PASS (all reps)' if all_ok else 'FAIL (see detail)'
            print(
                f"{scenario_name:<32}{config_name:<18}{avg_out:>8}"
                f"{avg_eval:>12}{avg_wall:>12}{correctness:>14}"
            )


def main() -> None:
    llm = ChatOllama(model=MODEL, temperature=TEMPERATURE)
    tools = build_tools()

    scenarios = [
        scenario_many_to_one(),
        scenario_relaxed_segments(),
        scenario_follow_up_required(),
        scenario_completion_round(),
    ]

    all_results = []
    for scenario in scenarios:
        print(f"\n### scenario: {scenario.name} ###")
        print(f"    {scenario.description}")
        results = run_scenario(llm, tools, scenario)
        for result in results:
            print_run(result)
        all_results.extend(results)

    summarize(all_results)


if __name__ == '__main__':
    main()
