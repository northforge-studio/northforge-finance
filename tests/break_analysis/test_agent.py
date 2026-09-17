from uuid import uuid4
from datetime import date
from decimal import Decimal

import pytest

from core.logging import short_id
from registry.models import GLSegmentType

from break_analysis.agent import BreakAnalysisAgent
from break_analysis.tools.registry import RegistryTools
from break_analysis.models import (
    BreakAnalysisConclusion,
    BreakCase,
    BreakRecord,
    BreakTopology,
)
from gl.models import GLSegments


AS_OF_DATE = date(2026, 1, 1)


def _segments(**overrides) -> GLSegments:
    defaults = dict(
        entity_cd='USM',
        branch_cd='100',
        dept_cd='4000',
        gl_account='123456',
        sub_account='001',
        affiliate_cd='AFF1',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
    )
    defaults.update(overrides)
    return GLSegments(**defaults)


def _record(**overrides) -> BreakRecord:
    defaults = dict(
        recon_result_id=uuid4(),
        workflow_run_id=uuid4(),
        as_of_date=AS_OF_DATE,
        segments=_segments(),
        accounted_currency='USD',
        interface_balance=Decimal('100.00'),
        gl_balance=Decimal('100.00'),
        difference_amount=Decimal('0.00'),
    )
    defaults.update(overrides)
    return BreakRecord(**defaults)


def _break_case(**overrides) -> BreakCase:
    defaults = dict(
        case_id=uuid4(),
        topology=BreakTopology.AMBIGUOUS,
        investigation_records=(_record(), _record()),
        pivot=None,
        evidence=None,
    )
    defaults.update(overrides)
    return BreakCase(**defaults)


def _tool_call(name='validate_segment', call_id='call_1', **arg_overrides) -> dict:
    args = dict(
        segment_type=GLSegmentType.ACCOUNT,
        segment_value='123456',
        business_dt=AS_OF_DATE,
    )
    args.update(arg_overrides)
    return {'name': name, 'args': args, 'id': call_id}


class _FakeMessage:
    def __init__(self, tool_calls=(), usage_metadata=None):
        self.tool_calls = list(tool_calls)
        self.usage_metadata = usage_metadata


class _FakeBoundLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    def invoke(self, messages):
        return self._responses.pop(0)


class _FakeStructuredLLM:
    def __init__(self, parsed=None, parsing_error=None, usage_metadata=None):
        self._parsed = parsed
        self._parsing_error = parsing_error
        self._usage_metadata = usage_metadata

    def invoke(self, messages):
        return {
            'raw': _FakeMessage(usage_metadata=self._usage_metadata),
            'parsed': self._parsed,
            'parsing_error': self._parsing_error,
        }


class _FakeLLM:
    def __init__(self, responses, parsed=None, parsing_error=None, conclusion_usage_metadata=None):
        self._bound = _FakeBoundLLM(responses)
        self._structured = _FakeStructuredLLM(
            parsed=parsed,
            parsing_error=parsing_error,
            usage_metadata=conclusion_usage_metadata,
        )

    def bind_tools(self, tools, reasoning=None):
        return self._bound

    def with_structured_output(self, schema, method=None, include_raw=False):
        return self._structured


class _FakeRegistryClient:
    def __init__(self, is_valid=True, raise_error=False):
        self._is_valid = is_valid
        self._raise_error = raise_error
        self.calls = []

    def validate_segment(self, segment_type, business_dt, segment_value):
        if self._raise_error:
            raise RuntimeError('registry unavailable')

        self.calls.append((segment_type, business_dt, segment_value))
        return self._is_valid


_CONCLUSION = BreakAnalysisConclusion(
    status='EXPLAINED',
    root_cause=None,
    explanation='Segment is valid; break explained by timing.',
)


def _agent(
    responses,
    registry_client=None,
    conclusion=None,
    parsing_error=None,
    conclusion_usage_metadata=None,
    **kwargs
) -> BreakAnalysisAgent:
    registry_tools = RegistryTools(registry_client=registry_client or _FakeRegistryClient())
    parsed = (
        None if parsing_error is not None
        else (conclusion if conclusion is not None else _CONCLUSION)
    )
    llm = _FakeLLM(
        responses,
        parsed=parsed,
        parsing_error=parsing_error,
        conclusion_usage_metadata=conclusion_usage_metadata,
    )
    return BreakAnalysisAgent(llm=llm, registry_tools=registry_tools, **kwargs)


# -- logging --------------------------------------------------------------

def test_analyze_logs_start_line_with_case_context(caplog):
    break_case = _break_case()
    agent = _agent(responses=[_FakeMessage()])

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        agent.analyze(break_case)

    start_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'Analyzing break case' in r.message
    ]
    assert len(start_records) == 1
    message = start_records[0].message
    assert f'case_id={short_id(break_case.case_id)}' in message
    assert str(break_case.case_id) not in message
    assert 'topology=AMBIGUOUS' in message
    assert 'records=2' in message


def test_analyze_logs_end_summary_with_status_and_counts(caplog):
    break_case = _break_case()
    agent = _agent(
        responses=[
            _FakeMessage(
                tool_calls=[_tool_call()],
                usage_metadata={'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120},
            ),
            _FakeMessage(
                usage_metadata={'input_tokens': 150, 'output_tokens': 10, 'total_tokens': 160},
            ),
        ],
        conclusion_usage_metadata={'input_tokens': 50, 'output_tokens': 5, 'total_tokens': 55},
    )

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        result = agent.analyze(break_case)

    summary_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'Break case analyzed' in r.message
    ]
    assert len(summary_records) == 1
    message = summary_records[0].message
    assert f'status={result.status}' in message
    assert 'tool_rounds=1' in message
    assert 'tool_calls=1' in message
    assert 'unique_tool_calls=1' in message
    # 2 tool-calling turns + 1 structured-output conclusion turn.
    assert 'llm_calls=3' in message
    assert 'llm_input_tokens=300' in message
    assert 'llm_output_tokens=35' in message
    assert 'duration_ms=' in message


def test_analyze_logs_each_llm_invocation_with_usage_and_duration(caplog):
    break_case = _break_case()
    agent = _agent(
        responses=[
            _FakeMessage(
                tool_calls=[_tool_call()],
                usage_metadata={'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120},
            ),
            _FakeMessage(
                usage_metadata={'input_tokens': 150, 'output_tokens': 10, 'total_tokens': 160},
            ),
        ],
        conclusion_usage_metadata={'input_tokens': 50, 'output_tokens': 5, 'total_tokens': 55},
    )

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        agent.analyze(break_case)

    llm_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'LLM invoked' in r.message
    ]
    # Fires once per LLM turn: the initial decision, the final
    # tool-call-free turn that ends the loop, and the structured-output
    # conclusion turn.
    assert len(llm_records) == 3

    first_message = llm_records[0].message
    assert 'round=1' in first_message
    assert 'tool_calls=1' in first_message
    assert 'input_tokens=100' in first_message
    assert 'output_tokens=20' in first_message
    assert 'total_tokens=120' in first_message
    assert 'duration_ms=' in first_message

    second_message = llm_records[1].message
    assert 'round=2' in second_message
    assert 'tool_calls=0' in second_message
    assert 'input_tokens=150' in second_message
    assert 'output_tokens=10' in second_message
    assert 'total_tokens=160' in second_message

    third_message = llm_records[2].message
    assert 'round=3' in third_message
    # The structured-output round isn't tool-bound, so it carries no
    # tool_calls field.
    assert 'tool_calls=' not in third_message
    assert 'input_tokens=50' in third_message
    assert 'output_tokens=5' in third_message
    assert 'total_tokens=55' in third_message
    assert 'duration_ms=' in third_message


def test_analyze_logs_invoking_llm_before_each_llm_invocation_with_matching_round(caplog):
    break_case = _break_case()
    agent = _agent(responses=[
        _FakeMessage(tool_calls=[_tool_call()]),
        _FakeMessage(),
    ])

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        agent.analyze(break_case)

    relevant_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and r.message.startswith(('Invoking LLM', 'LLM invoked'))
    ]

    # 3 LLM turns total: two tool-bound turns plus the structured-output
    # conclusion turn, each as an Invoking/invoked pair.
    assert [r.message.split(' | ')[0] for r in relevant_records] == [
        'Invoking LLM', 'LLM invoked',
        'Invoking LLM', 'LLM invoked',
        'Invoking LLM', 'LLM invoked',
    ]
    assert 'round=1' in relevant_records[0].message
    assert 'round=1' in relevant_records[1].message
    assert 'round=2' in relevant_records[2].message
    assert 'round=2' in relevant_records[3].message
    assert 'round=3' in relevant_records[4].message
    assert 'round=3' in relevant_records[5].message


def test_analyze_logs_llm_invocation_with_none_when_usage_metadata_unavailable(caplog):
    break_case = _break_case()
    agent = _agent(responses=[_FakeMessage(usage_metadata=None)])

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        agent.analyze(break_case)

    llm_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'LLM invoked' in r.message
    ]
    # The tool-bound turn and the structured-output conclusion turn both
    # go through the same usage_metadata-unavailable fallback.
    assert len(llm_records) == 2
    for record in llm_records:
        assert 'input_tokens=None' in record.message
        assert 'output_tokens=None' in record.message
        assert 'total_tokens=None' in record.message


def test_analyze_logs_each_tool_invocation_with_duration(caplog):
    break_case = _break_case()
    agent = _agent(responses=[
        _FakeMessage(tool_calls=[_tool_call()]),
        _FakeMessage(),
    ])

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        agent.analyze(break_case)

    tool_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'Tool invoked' in r.message
    ]
    assert len(tool_records) == 1
    message = tool_records[0].message
    assert 'tool=validate_segment' in message
    assert 'duration_ms=' in message
    # Args are rendered as JSON, not a Python dict repr: dates come out as
    # plain ISO strings instead of datetime.date(...) reprs.
    assert '"business_dt": "2026-01-01"' in message
    assert 'datetime.date' not in message


def test_analyze_logs_cache_hit_at_debug_level_for_repeated_tool_call(caplog):
    break_case = _break_case()
    repeated_call = [_tool_call(call_id='call_1'), _tool_call(call_id='call_2')]
    agent = _agent(responses=[
        _FakeMessage(tool_calls=repeated_call),
        _FakeMessage(),
    ])

    with caplog.at_level('DEBUG', logger='break_analysis.agent'):
        agent.analyze(break_case)

    invoked_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'Tool invoked' in r.message
    ]
    cache_hit_records = [
        r for r in caplog.records
        if r.levelname == 'DEBUG' and 'Tool cache hit' in r.message
    ]
    assert len(invoked_records) == 1
    assert len(cache_hit_records) == 1


def test_analyze_logs_and_raises_on_unknown_tool(caplog):
    break_case = _break_case()
    agent = _agent(responses=[
        _FakeMessage(tool_calls=[_tool_call(name='not_a_real_tool')]),
    ])

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        with pytest.raises(RuntimeError, match='Unknown tool requested by agent'):
            agent.analyze(break_case)

    error_records = [
        r for r in caplog.records
        if r.levelname == 'ERROR' and 'Unknown tool requested' in r.message
    ]
    assert len(error_records) == 1
    assert 'tool=not_a_real_tool' in error_records[0].message


def test_analyze_logs_exception_and_raises_on_tool_failure(caplog):
    break_case = _break_case()
    agent = _agent(
        responses=[_FakeMessage(tool_calls=[_tool_call()])],
        registry_client=_FakeRegistryClient(raise_error=True),
    )

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        with pytest.raises(RuntimeError, match='validate_segment.*failed'):
            agent.analyze(break_case)

    exception_records = [
        r for r in caplog.records
        if r.levelname == 'ERROR' and 'Tool failed' in r.message and r.exc_info
    ]
    assert len(exception_records) == 1
    assert 'tool=validate_segment' in exception_records[0].message


def test_analyze_logs_and_raises_on_max_tool_rounds_exceeded(caplog):
    break_case = _break_case()
    agent = _agent(
        responses=[
            _FakeMessage(tool_calls=[_tool_call(call_id='call_1')]),
            _FakeMessage(tool_calls=[_tool_call(call_id='call_2')]),
        ],
        max_tool_rounds=1,
    )

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        with pytest.raises(RuntimeError, match='Maximum tool rounds exceeded'):
            agent.analyze(break_case)

    error_records = [
        r for r in caplog.records
        if r.levelname == 'ERROR' and 'Max tool rounds exceeded' in r.message
    ]
    assert len(error_records) == 1
    assert 'max_rounds=1' in error_records[0].message


def test_analyze_logs_and_raises_on_structured_output_parsing_error(caplog):
    break_case = _break_case()
    original_error = ValueError('model did not return valid JSON')
    agent = _agent(
        responses=[_FakeMessage()],
        parsing_error=original_error,
    )

    with caplog.at_level('INFO', logger='break_analysis.agent'):
        with pytest.raises(RuntimeError, match='Failed to parse structured output') as exc_info:
            agent.analyze(break_case)

    assert exc_info.value.__cause__ is original_error

    error_records = [
        r for r in caplog.records
        if r.levelname == 'ERROR' and 'Structured output parsing failed' in r.message
    ]
    assert len(error_records) == 1
    assert f'case_id={short_id(break_case.case_id)}' in error_records[0].message
    assert str(break_case.case_id) not in error_records[0].message
