import re
from typing import Any
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from break_analysis.agent import BreakAnalysisAgent
from break_analysis.exceptions import (
    InvalidToolArgumentsError,
    MaxToolRoundsError,
    ModelTransientError,
    StructuredOutputError,
    ToolExecutionError,
    ToolTransientError,
    UnknownToolError,
)
from break_analysis.graph import BreakAnalysisGraph
from break_analysis.models import (
    BreakAnalysisConclusion,
    BreakAnalysisStatus,
    BreakCase,
    BreakTopology,
)
from break_analysis.tools.registry import RegistryTools
from core.logging import short_id
from registry.models import GLSegmentType
from tests.break_analysis.factories import make_break_record
from tests.support.constants import AS_OF_DATE

_CONCLUSION = BreakAnalysisConclusion(
    status=BreakAnalysisStatus.EXPLAINED,
    findings=(),
    explanation='Segment is valid; break explained by timing.',
)


# -- fakes -----------------------------------------------------------------


class _FakeTransientModelError(Exception):
    """A provider error that _FakeModelProvider classifies as transient."""


class _FakeBoundLLM:
    """The tool-bound LLM, replaying the scripted responses in order and
    raising any scripted exception instead of returning it."""

    def __init__(self, responses):
        self._responses = list(responses)

    def invoke(self, messages):
        response = self._responses.pop(0)

        if isinstance(response, Exception):
            raise response

        return response


class _FakeStructuredLLM:
    """The structured-output LLM, returning a fixed parsed conclusion and
    recording the messages it was invoked with; scripted errors are raised,
    one per invocation, before the conclusion is returned."""

    def __init__(self, parsed=None, parsing_error=None, usage_metadata=None, errors=()):
        self._parsed = parsed
        self._parsing_error = parsing_error
        self._usage_metadata = usage_metadata
        self._errors = list(errors)
        self.messages = None

    def invoke(self, messages):
        if self._errors:
            raise self._errors.pop(0)

        self.messages = messages
        return {
            'raw': AIMessage(content='', usage_metadata=self._usage_metadata),
            'parsed': self._parsed,
            'parsing_error': self._parsing_error,
        }


class _FakeLLM:
    """A chat model stub exposing bind_tools and with_structured_output."""

    def __init__(
        self,
        responses,
        parsed=None,
        parsing_error=None,
        conclusion_usage_metadata=None,
        conclusion_errors=(),
    ):
        self.bound = _FakeBoundLLM(responses)
        self.structured = _FakeStructuredLLM(
            parsed=parsed,
            parsing_error=parsing_error,
            usage_metadata=conclusion_usage_metadata,
            errors=conclusion_errors,
        )

    def bind_tools(self, tools, reasoning=None):
        return self.bound

    def with_structured_output(self, schema, method=None, include_raw=False):
        return self.structured


class _FakeModelProvider:
    """Implements ChatModelProvider over a _FakeLLM; only
    _FakeTransientModelError is classified as transient."""

    def __init__(self, llm):
        self._llm = llm

    def chat_model(self) -> Any:
        return self._llm

    def is_transient_error(self, exc):
        return isinstance(exc, _FakeTransientModelError)


class _FakeRegistryClient:
    """Implements RegistryClientProtocol; validate_segment optionally raises
    ToolTransientError for its first transient_failures attempts, or always
    raises RuntimeError, and counts every attempt; get_segment_details is
    unsupported."""

    def __init__(self, is_valid=True, raise_error=False, transient_failures=0):
        self._is_valid = is_valid
        self._raise_error = raise_error
        self._transient_failures = transient_failures
        self.calls = []
        self.attempts = 0

    def validate_segment(self, segment, business_dt, segment_cd):
        self.attempts += 1

        if self.attempts <= self._transient_failures:
            raise ToolTransientError('registry timed out')

        if self._raise_error:
            raise RuntimeError('registry unavailable')

        self.calls.append((segment, business_dt, segment_cd))
        return self._is_valid

    def get_segment_details(self, segment, business_dt, segment_cd):
        raise NotImplementedError('_FakeRegistryClient.get_segment_details')


class _FakeAtlasTools:
    """Implements AtlasToolsProtocol; investigate_resolution is unsupported."""

    def investigate_resolution(self, workflow_run_id, recon_result_id, segment_type):
        raise NotImplementedError('_FakeAtlasTools.investigate_resolution')


# -- fixtures --------------------------------------------------------------


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    """Records retry backoff delays instead of sleeping."""
    recorded: list[float] = []
    monkeypatch.setattr('break_analysis.graph.time.sleep', recorded.append)
    return recorded


# -- helpers ---------------------------------------------------------------


def _make_break_case(**overrides) -> BreakCase:
    defaults: dict[str, Any] = dict(
        case_id=uuid4(),
        topology=BreakTopology.AMBIGUOUS,
        investigation_records=(make_break_record(), make_break_record()),
        pivot=None,
        evidence=None,
    )
    defaults.update(overrides)
    return BreakCase(**defaults)


def _make_ai_message(tool_calls=(), usage_metadata=None) -> AIMessage:
    return AIMessage(
        content='', tool_calls=list(tool_calls), usage_metadata=usage_metadata
    )


def _make_tool_call(name='validate_segment', call_id='call_1', **arg_overrides) -> dict:
    args = dict(
        segment_type=GLSegmentType.ACCOUNT,
        segment_value='123456',
        business_dt=AS_OF_DATE,
    )
    args.update(arg_overrides)
    return {'name': name, 'args': args, 'id': call_id}


def _make_llm(
    responses,
    conclusion=None,
    parsing_error=None,
    conclusion_usage_metadata=None,
    conclusion_errors=(),
) -> _FakeLLM:
    parsed = (
        None
        if parsing_error is not None
        else (conclusion if conclusion is not None else _CONCLUSION)
    )
    return _FakeLLM(
        responses,
        parsed=parsed,
        parsing_error=parsing_error,
        conclusion_usage_metadata=conclusion_usage_metadata,
        conclusion_errors=conclusion_errors,
    )


def _make_agent(llm, registry_client=None, **kwargs) -> BreakAnalysisAgent:
    registry_tools = RegistryTools(
        registry_client=registry_client or _FakeRegistryClient()
    )
    return BreakAnalysisAgent(
        model_provider=_FakeModelProvider(llm),
        atlas_tools=_FakeAtlasTools(),
        registry_tools=registry_tools,
        **kwargs,
    )


def _lifecycle_events(records) -> list[tuple[str, str, str]]:
    """(event, node, levelname) for each Graph node lifecycle record."""
    events = []

    for record in records:
        match = re.search(r'Graph node (\w+) \|.* node=(\w+)', record.message)

        if match:
            events.append((match.group(1), match.group(2), record.levelname))

    return events


def _analysis_run_ids(records) -> list[str | None]:
    return [
        match.group(1) if match else None
        for match in (
            re.search(r'analysis_run_id=([0-9a-f-]+)', record.message)
            for record in records
        )
    ]


def _make_retry_agent(registry_client) -> BreakAnalysisAgent:
    return _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call()]),
                _make_ai_message(),
            ]
        ),
        registry_client=registry_client,
    )


# -- analyze ---------------------------------------------------------------


def test_analyze_without_tool_calls_returns_result_from_conclusion():
    break_case = _make_break_case()
    agent = _make_agent(_make_llm(responses=[_make_ai_message()]))

    result = agent.analyze(break_case)

    assert result.case_id == break_case.case_id
    assert result.recon_result_ids == tuple(
        record.recon_result_id for record in break_case.all_records
    )
    assert result.status == _CONCLUSION.status
    assert result.findings == _CONCLUSION.findings
    assert result.explanation == _CONCLUSION.explanation


def test_analyze_with_tool_call_invokes_tool_once():
    registry_client = _FakeRegistryClient()
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call()]),
                _make_ai_message(),
            ]
        ),
        registry_client=registry_client,
    )

    agent.analyze(_make_break_case())

    assert registry_client.calls == [(GLSegmentType.ACCOUNT, AS_OF_DATE, '123456')]


def test_analyze_passes_gathered_evidence_to_conclusion():
    llm = _make_llm(
        responses=[
            _make_ai_message(tool_calls=[_make_tool_call()]),
            _make_ai_message(),
        ]
    )
    agent = _make_agent(llm)

    agent.analyze(_make_break_case())

    assert llm.structured.messages is not None
    evidence_message = llm.structured.messages[-1]
    assert isinstance(evidence_message, HumanMessage)
    assert isinstance(evidence_message.content, str)
    assert evidence_message.content.startswith('Gathered evidence:')
    assert '"tool_name": "validate_segment"' in evidence_message.content
    assert 'is_valid=True' in evidence_message.content


def test_analyze_conclusion_input_does_not_end_with_ai_message():
    # A trailing AIMessage is treated as an assistant prefill by Ollama,
    # which makes the conclusion model return empty content.
    llm = _make_llm(
        responses=[
            _make_ai_message(tool_calls=[_make_tool_call()]),
            _make_ai_message(),
        ]
    )
    agent = _make_agent(llm)

    agent.analyze(_make_break_case())

    assert llm.structured.messages is not None
    assert not any(isinstance(m, AIMessage) for m in llm.structured.messages)


# -- analyze: errors -------------------------------------------------------


def test_analyze_raises_on_unknown_tool():
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call(name='not_a_real_tool')]),
            ]
        )
    )

    with pytest.raises(UnknownToolError, match='Unknown tool requested by agent'):
        agent.analyze(_make_break_case())


def test_analyze_raises_on_invalid_tool_arguments():
    registry_client = _FakeRegistryClient()
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(
                    tool_calls=[_make_tool_call(segment_type='NOT_A_SEGMENT')]
                )
            ]
        ),
        registry_client=registry_client,
    )

    with pytest.raises(
        InvalidToolArgumentsError, match="Invalid arguments for tool 'validate_segment'"
    ) as exc_info:
        agent.analyze(_make_break_case())

    assert isinstance(exc_info.value.__cause__, ValidationError)
    assert registry_client.attempts == 0


def test_analyze_raises_on_tool_failure():
    agent = _make_agent(
        _make_llm(responses=[_make_ai_message(tool_calls=[_make_tool_call()])]),
        registry_client=_FakeRegistryClient(raise_error=True),
    )

    with pytest.raises(
        ToolExecutionError, match='validate_segment.*failed'
    ) as exc_info:
        agent.analyze(_make_break_case())

    assert not isinstance(exc_info.value, ToolTransientError)
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == 'registry unavailable'


def test_analyze_raises_on_max_tool_rounds_exceeded():
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call(call_id='call_1')]),
                _make_ai_message(tool_calls=[_make_tool_call(call_id='call_2')]),
                _make_ai_message(),
            ]
        ),
        max_tool_rounds=1,
    )

    with pytest.raises(MaxToolRoundsError, match='Maximum tool rounds exceeded'):
        agent.analyze(_make_break_case())


def test_analyze_raises_on_structured_output_parsing_error():
    original_error = ValueError('model did not return valid JSON')
    agent = _make_agent(
        _make_llm(responses=[_make_ai_message()], parsing_error=original_error)
    )

    with pytest.raises(
        StructuredOutputError, match='Failed to parse structured output'
    ) as exc_info:
        agent.analyze(_make_break_case())

    assert exc_info.value.__cause__ is original_error


# -- analyze: tool retry ---------------------------------------------------


def test_analyze_retries_tool_after_transient_failure(sleeps):
    registry_client = _FakeRegistryClient(transient_failures=2)
    agent = _make_retry_agent(registry_client)

    result = agent.analyze(_make_break_case())

    assert result.status == _CONCLUSION.status
    assert registry_client.attempts == 3
    assert registry_client.calls == [(GLSegmentType.ACCOUNT, AS_OF_DATE, '123456')]
    assert sleeps == [1, 2]


def test_analyze_raises_unwrapped_transient_error_when_tool_attempts_exhausted(
    sleeps,
):
    registry_client = _FakeRegistryClient(transient_failures=3)
    agent = _make_retry_agent(registry_client)

    with pytest.raises(ToolTransientError, match='registry timed out'):
        agent.analyze(_make_break_case())

    assert registry_client.attempts == 3
    assert registry_client.calls == []
    assert sleeps == [1, 2]


def test_analyze_does_not_retry_non_transient_tool_failure(sleeps):
    registry_client = _FakeRegistryClient(raise_error=True)
    agent = _make_retry_agent(registry_client)

    with pytest.raises(ToolExecutionError, match='validate_segment.*failed'):
        agent.analyze(_make_break_case())

    assert registry_client.attempts == 1
    assert sleeps == []


def test_invoke_tool_with_retry_rejects_non_positive_max_attempts():
    graph = BreakAnalysisGraph(
        model_provider=_FakeModelProvider(_make_llm(responses=[])),
        atlas_tools=_FakeAtlasTools(),
        registry_tools=RegistryTools(registry_client=_FakeRegistryClient()),
    )
    tool = graph._tool_registry['validate_segment']

    with pytest.raises(ValueError, match='max_attempts must be at least 1'):
        graph._invoke_tool_with_retry(
            tool,
            _make_tool_call()['args'],
            analysis_run_id='run',
            case_id='case',
            max_attempts=0,
        )


# -- analyze: model retry --------------------------------------------------


def test_analyze_retries_evidence_llm_after_transient_failure(sleeps):
    agent = _make_agent(
        _make_llm(
            responses=[
                _FakeTransientModelError('model busy'),
                _FakeTransientModelError('model busy'),
                _make_ai_message(),
            ]
        )
    )

    result = agent.analyze(_make_break_case())

    assert result.status == _CONCLUSION.status
    assert len(sleeps) == 2


def test_analyze_retries_conclusion_llm_after_transient_failure(sleeps):
    llm = _make_llm(
        responses=[_make_ai_message()],
        conclusion_errors=[_FakeTransientModelError('model busy')],
    )
    agent = _make_agent(llm)

    result = agent.analyze(_make_break_case())

    assert result.status == _CONCLUSION.status
    assert llm.structured.messages is not None
    assert len(sleeps) == 1


def test_analyze_raises_model_transient_error_when_llm_attempts_exhausted(sleeps):
    agent = _make_agent(
        _make_llm(responses=[_FakeTransientModelError('model busy')] * 3)
    )

    with pytest.raises(ModelTransientError, match='Transient LLM failure') as exc_info:
        agent.analyze(_make_break_case())

    assert isinstance(exc_info.value.__cause__, _FakeTransientModelError)
    assert len(sleeps) == 2


def test_analyze_does_not_retry_non_transient_llm_failure(sleeps):
    agent = _make_agent(
        _make_llm(responses=[RuntimeError('model misconfigured'), _make_ai_message()])
    )

    with pytest.raises(RuntimeError, match='model misconfigured'):
        agent.analyze(_make_break_case())

    assert sleeps == []


# -- analyze: node lifecycle -----------------------------------------------


def test_analyze_logs_node_lifecycle_in_execution_order(caplog):
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call()]),
                _make_ai_message(),
            ]
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(_make_break_case())

    nodes = [
        'initialize_analysis',
        'gather_evidence',
        'execute_tool_calls',
        'gather_evidence',
        'conclude',
    ]
    events = _lifecycle_events(caplog.records)
    assert [node for event, node, _ in events if event == 'started'] == nodes
    assert [node for event, node, _ in events if event == 'completed'] == nodes
    completed_records = [
        r for r in caplog.records if 'Graph node completed' in r.message
    ]
    assert all('duration_ms=' in r.message for r in completed_records)


def test_analyze_tags_all_logs_with_one_analysis_run_id_per_invocation(caplog):
    agent = _make_agent(_make_llm(responses=[_make_ai_message(), _make_ai_message()]))
    break_case = _make_break_case()

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(break_case)
        first_run_ids = _analysis_run_ids(caplog.records)
        caplog.clear()
        agent.analyze(break_case)
        second_run_ids = _analysis_run_ids(caplog.records)

    assert None not in first_run_ids
    assert None not in second_run_ids
    assert len(set(first_run_ids)) == 1
    assert len(set(second_run_ids)) == 1
    assert first_run_ids[0] != second_run_ids[0]


def test_analyze_logs_node_failed_error_without_traceback(caplog):
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call(name='not_a_real_tool')]),
            ]
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        with pytest.raises(RuntimeError, match='Unknown tool requested by agent'):
            agent.analyze(_make_break_case())

    failed_records = [r for r in caplog.records if 'Graph node failed' in r.message]
    assert len(failed_records) == 1
    assert failed_records[0].levelname == 'ERROR'
    assert 'node=execute_tool_calls' in failed_records[0].message
    assert 'duration_ms=' in failed_records[0].message
    assert 'error=UnknownToolError' in failed_records[0].message
    assert not failed_records[0].exc_info


def test_analyze_logs_node_failed_warning_then_restart_on_llm_retry(caplog, sleeps):
    agent = _make_agent(
        _make_llm(
            responses=[_FakeTransientModelError('model busy'), _make_ai_message()]
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(_make_break_case())

    gather_events = [
        (event, levelname)
        for event, node, levelname in _lifecycle_events(caplog.records)
        if node == 'gather_evidence'
    ]
    assert gather_events == [
        ('started', 'INFO'),
        ('failed', 'WARNING'),
        ('started', 'INFO'),
        ('completed', 'INFO'),
    ]


# -- analyze: logging ------------------------------------------------------


def test_analyze_logs_start_line_with_case_context(caplog):
    break_case = _make_break_case()
    agent = _make_agent(_make_llm(responses=[_make_ai_message()]))

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(break_case)

    start_records = [
        r
        for r in caplog.records
        if r.levelname == 'INFO' and 'Analyzing break case' in r.message
    ]
    assert len(start_records) == 1
    message = start_records[0].message
    assert f'case_id={short_id(break_case.case_id)}' in message
    assert str(break_case.case_id) not in message
    assert 'topology=AMBIGUOUS' in message
    assert 'records=2' in message


def test_analyze_logs_end_summary_with_status_and_counts(caplog):
    break_case = _make_break_case()
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(
                    tool_calls=[_make_tool_call()],
                    usage_metadata={
                        'input_tokens': 100,
                        'output_tokens': 20,
                        'total_tokens': 120,
                    },
                ),
                _make_ai_message(
                    usage_metadata={
                        'input_tokens': 150,
                        'output_tokens': 10,
                        'total_tokens': 160,
                    },
                ),
            ],
            conclusion_usage_metadata={
                'input_tokens': 50,
                'output_tokens': 5,
                'total_tokens': 55,
            },
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        result = agent.analyze(break_case)

    summary_records = [
        r
        for r in caplog.records
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
    break_case = _make_break_case()
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(
                    tool_calls=[_make_tool_call()],
                    usage_metadata={
                        'input_tokens': 100,
                        'output_tokens': 20,
                        'total_tokens': 120,
                    },
                ),
                _make_ai_message(
                    usage_metadata={
                        'input_tokens': 150,
                        'output_tokens': 10,
                        'total_tokens': 160,
                    },
                ),
            ],
            conclusion_usage_metadata={
                'input_tokens': 50,
                'output_tokens': 5,
                'total_tokens': 55,
            },
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(break_case)

    llm_records = [
        r
        for r in caplog.records
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


def test_analyze_logs_invoking_llm_before_each_invocation_with_matching_round(caplog):
    break_case = _make_break_case()
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call()]),
                _make_ai_message(),
            ]
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(break_case)

    relevant_records = [
        r
        for r in caplog.records
        if r.levelname == 'INFO'
        and r.message.startswith(('Invoking LLM', 'LLM invoked'))
    ]

    # 3 LLM turns total: two tool-bound turns plus the structured-output
    # conclusion turn, each as an Invoking/invoked pair.
    assert [r.message.split(' | ')[0] for r in relevant_records] == [
        'Invoking LLM',
        'LLM invoked',
        'Invoking LLM',
        'LLM invoked',
        'Invoking LLM',
        'LLM invoked',
    ]
    assert 'round=1' in relevant_records[0].message
    assert 'round=1' in relevant_records[1].message
    assert 'round=2' in relevant_records[2].message
    assert 'round=2' in relevant_records[3].message
    assert 'round=3' in relevant_records[4].message
    assert 'round=3' in relevant_records[5].message


def test_analyze_logs_llm_invocation_with_none_when_usage_metadata_unavailable(caplog):
    break_case = _make_break_case()
    agent = _make_agent(_make_llm(responses=[_make_ai_message(usage_metadata=None)]))

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(break_case)

    llm_records = [
        r
        for r in caplog.records
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
    break_case = _make_break_case()
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call()]),
                _make_ai_message(),
            ]
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(break_case)

    tool_records = [
        r
        for r in caplog.records
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
    break_case = _make_break_case()
    repeated_call = [
        _make_tool_call(call_id='call_1'),
        _make_tool_call(call_id='call_2'),
    ]
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=repeated_call),
                _make_ai_message(),
            ]
        )
    )

    with caplog.at_level('DEBUG', logger='break_analysis.graph'):
        agent.analyze(break_case)

    invoked_records = [
        r
        for r in caplog.records
        if r.levelname == 'INFO' and 'Tool invoked' in r.message
    ]
    cache_hit_records = [
        r
        for r in caplog.records
        if r.levelname == 'DEBUG' and 'Tool cache hit' in r.message
    ]
    assert len(invoked_records) == 1
    assert len(cache_hit_records) == 1


def test_analyze_logs_warning_for_each_tool_retry(caplog, sleeps):
    break_case = _make_break_case()
    agent = _make_retry_agent(_FakeRegistryClient(transient_failures=2))

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(break_case)

    retry_records = [
        r
        for r in caplog.records
        if r.levelname == 'WARNING' and 'Tool transient failure' in r.message
    ]
    assert len(retry_records) == 2
    first_message = retry_records[0].message
    assert f'case_id={short_id(break_case.case_id)}' in first_message
    assert 'tool=validate_segment' in first_message
    assert 'attempt=1/3' in first_message
    assert 'delay_s=1' in first_message
    assert 'attempt=2/3' in retry_records[1].message
    assert 'delay_s=2' in retry_records[1].message
    assert all(r.exc_info for r in retry_records)


def test_analyze_logs_warning_without_error_for_recovered_llm_failure(caplog, sleeps):
    break_case = _make_break_case()
    agent = _make_agent(
        _make_llm(
            responses=[_FakeTransientModelError('model busy'), _make_ai_message()]
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        agent.analyze(break_case)

    warning_records = [
        r
        for r in caplog.records
        if r.levelname == 'WARNING' and 'LLM transient failure' in r.message
    ]
    assert len(warning_records) == 1
    assert f'case_id={short_id(break_case.case_id)}' in warning_records[0].message
    assert 'round=1' in warning_records[0].message
    assert warning_records[0].exc_info
    assert not [r for r in caplog.records if r.levelname == 'ERROR']


def test_analyze_logs_exception_when_llm_retries_exhausted(caplog, sleeps):
    break_case = _make_break_case()
    agent = _make_agent(
        _make_llm(responses=[_FakeTransientModelError('model busy')] * 3)
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        with pytest.raises(ModelTransientError, match='Transient LLM failure'):
            agent.analyze(break_case)

    warning_records = [
        r
        for r in caplog.records
        if r.levelname == 'WARNING' and 'LLM transient failure' in r.message
    ]
    error_records = [r for r in caplog.records if r.levelname == 'ERROR']
    assert len(warning_records) == 3
    assert len(error_records) == 1
    assert 'LLM retries exhausted' in error_records[0].message
    assert f'case_id={short_id(break_case.case_id)}' in error_records[0].message
    assert error_records[0].exc_info


def test_analyze_logs_exception_on_non_transient_llm_failure(caplog):
    agent = _make_agent(_make_llm(responses=[RuntimeError('model misconfigured')]))

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        with pytest.raises(RuntimeError, match='model misconfigured'):
            agent.analyze(_make_break_case())

    error_records = [
        r
        for r in caplog.records
        if r.levelname == 'ERROR' and 'LLM invocation failed' in r.message
    ]
    assert len(error_records) == 1
    assert error_records[0].exc_info
    assert not [r for r in caplog.records if r.levelname == 'WARNING']


def test_analyze_logs_error_on_unknown_tool(caplog):
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call(name='not_a_real_tool')]),
            ]
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        with pytest.raises(RuntimeError, match='Unknown tool requested by agent'):
            agent.analyze(_make_break_case())

    error_records = [
        r
        for r in caplog.records
        if r.levelname == 'ERROR' and 'Unknown tool requested' in r.message
    ]
    assert len(error_records) == 1
    assert 'tool=not_a_real_tool' in error_records[0].message


def test_analyze_logs_exception_on_tool_failure(caplog):
    agent = _make_agent(
        _make_llm(responses=[_make_ai_message(tool_calls=[_make_tool_call()])]),
        registry_client=_FakeRegistryClient(raise_error=True),
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        with pytest.raises(RuntimeError, match='validate_segment.*failed'):
            agent.analyze(_make_break_case())

    exception_records = [
        r
        for r in caplog.records
        if r.levelname == 'ERROR' and 'Tool failed' in r.message and r.exc_info
    ]
    assert len(exception_records) == 1
    assert 'tool=validate_segment' in exception_records[0].message


def test_analyze_logs_error_on_max_tool_rounds_exceeded(caplog):
    agent = _make_agent(
        _make_llm(
            responses=[
                _make_ai_message(tool_calls=[_make_tool_call(call_id='call_1')]),
                _make_ai_message(tool_calls=[_make_tool_call(call_id='call_2')]),
            ]
        ),
        max_tool_rounds=1,
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        with pytest.raises(RuntimeError, match='Maximum tool rounds exceeded'):
            agent.analyze(_make_break_case())

    error_records = [
        r
        for r in caplog.records
        if r.levelname == 'ERROR' and 'Max tool rounds exceeded' in r.message
    ]
    assert len(error_records) == 1
    assert 'max_rounds=1' in error_records[0].message


def test_analyze_logs_error_on_structured_output_parsing_error(caplog):
    break_case = _make_break_case()
    agent = _make_agent(
        _make_llm(
            responses=[_make_ai_message()],
            parsing_error=ValueError('model did not return valid JSON'),
        )
    )

    with caplog.at_level('INFO', logger='break_analysis.graph'):
        with pytest.raises(RuntimeError, match='Failed to parse structured output'):
            agent.analyze(break_case)

    error_records = [
        r
        for r in caplog.records
        if r.levelname == 'ERROR' and 'Structured output parsing failed' in r.message
    ]
    assert len(error_records) == 1
    assert f'case_id={short_id(break_case.case_id)}' in error_records[0].message
    assert str(break_case.case_id) not in error_records[0].message
