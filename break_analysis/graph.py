import json
import logging
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TypedDict
from uuid import uuid4

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy
from pydantic import BaseModel, ValidationError

from break_analysis.exceptions import (
    BreakAnalysisError,
    InvalidToolArgumentsError,
    MaxToolRoundsError,
    ModelTransientError,
    StructuredOutputError,
    ToolExecutionError,
    ToolTransientError,
    UnknownToolError,
)
from break_analysis.model_provider import ChatModelProvider
from break_analysis.models import (
    BreakAnalysisConclusion,
    BreakAnalysisResult,
    BreakCase,
    BreakInvestigationContext,
)
from break_analysis.prompts import CONCLUSION_SYSTEM_PROMPT, EVIDENCE_SYSTEM_PROMPT
from break_analysis.tools.atlas import (
    AtlasToolsProtocol,
    InvestigateAtlasResolutionInput,
)
from break_analysis.tools.registry import RegistryToolsProtocol, ValidateSegmentInput
from core.logging import get_logger, short_id

logger = get_logger(__name__)


class BreakAnalysisGraphInput(TypedDict):
    break_case: BreakCase


class _GraphRunInput(BreakAnalysisGraphInput):
    analysis_run_id: str


class BreakAnalysisGraphOutput(TypedDict):
    result: BreakAnalysisResult | None


class GatheredEvidence(TypedDict):
    tool_name: str
    tool_args: dict
    result: object


class BreakAnalysisGraphState(TypedDict):
    analysis_run_id: str
    break_case: BreakCase
    result: BreakAnalysisResult | None

    break_context: BreakInvestigationContext | None

    evidence_trail: list[BaseMessage]
    gathered_evidence: list[GatheredEvidence]

    llm_round: int
    llm_input_tokens: int
    llm_output_tokens: int

    tool_round: int
    tool_calls_total: int
    tool_cache: dict[str, object]


class BreakAnalysisGraph:
    def __init__(
        self,
        model_provider: ChatModelProvider,
        atlas_tools: AtlasToolsProtocol,
        registry_tools: RegistryToolsProtocol,
        max_tool_rounds: int = 10,
    ):
        if max_tool_rounds < 1:
            raise ValueError('max_tool_rounds must be at least 1.')

        self._model_provider = model_provider
        llm = model_provider.chat_model()
        self._atlas_tools = atlas_tools
        self._registry_tools = registry_tools
        self._max_tool_rounds = max_tool_rounds

        self._tools = [
            StructuredTool.from_function(
                func=self._registry_tools.validate_segment,
                name='validate_segment',
                description=(
                    'Validate whether a GL segment value is active '
                    'and valid in Registry.'
                ),
                args_schema=ValidateSegmentInput,
            ),
            StructuredTool.from_function(
                func=self._registry_tools.get_segment_details,
                name='get_segment_details',
                description=(
                    'Retrieve the details of a GL segment value from the Registry, '
                    'including its existence and status.'
                ),
                args_schema=ValidateSegmentInput,
            ),
            StructuredTool.from_function(
                func=self._atlas_tools.investigate_resolution,
                name='investigate_resolution',
                description=(
                    'Investigate why a blank or unresolved GL segment value '
                    'failed to resolve through Atlas mapping.'
                ),
                args_schema=InvestigateAtlasResolutionInput,
            ),
        ]

        self._llm_with_tools = llm.bind_tools(self._tools, reasoning=True)
        self._tool_registry = {tool.name: tool for tool in self._tools}

        self._llm_with_structure = llm.with_structured_output(
            BreakAnalysisConclusion, method='json_schema', include_raw=True
        )
        self._graph = self._build()

    def invoke(self, graph_input: BreakAnalysisGraphInput) -> BreakAnalysisGraphOutput:
        break_case = graph_input['break_case']
        analysis_run_id = str(uuid4())
        start = time.monotonic()

        logger.info(
            'Analyzing break case | analysis_run_id=%s | case_id=%s | '
            'workflow_run_id=%s | topology=%s | records=%s',
            analysis_run_id,
            short_id(break_case.case_id),
            short_id(break_case.all_records[0].workflow_run_id),
            break_case.topology,
            len(break_case.all_records),
        )

        try:
            final_state = self._graph.invoke(
                _GraphRunInput(break_case=break_case, analysis_run_id=analysis_run_id)
            )
        except ModelTransientError:
            logger.exception(
                'LLM retries exhausted | analysis_run_id=%s | case_id=%s',
                analysis_run_id,
                short_id(break_case.case_id),
            )
            raise

        self._log_analysis_summary(
            final_state, round((time.monotonic() - start) * 1000)
        )

        return BreakAnalysisGraphOutput(result=final_state['result'])

    def _build(self):
        graph = StateGraph(BreakAnalysisGraphState, input_schema=_GraphRunInput)

        graph.add_node('initialize_analysis', self._initialize_analysis)
        model_retry_policy = RetryPolicy(
            initial_interval=1.0,
            backoff_factor=2.0,
            max_attempts=3,
            jitter=True,
            retry_on=ModelTransientError,
        )

        graph.add_node(
            'gather_evidence', self._gather_evidence, retry_policy=model_retry_policy
        )
        graph.add_node('execute_tool_calls', self._execute_tool_calls)
        graph.add_node('conclude', self._conclude, retry_policy=model_retry_policy)

        graph.add_edge(START, 'initialize_analysis')
        graph.add_edge('initialize_analysis', 'gather_evidence')
        graph.add_conditional_edges(
            'gather_evidence',
            self._route_after_evidence,
            {
                'execute_tool_calls': 'execute_tool_calls',
                'conclude': 'conclude',
            },
        )
        graph.add_edge('execute_tool_calls', 'gather_evidence')
        graph.add_edge('conclude', END)

        return graph.compile()

    # Node
    def _initialize_analysis(self, state: BreakAnalysisGraphState) -> dict:
        with self._node_lifecycle('initialize_analysis', state):
            break_case = state['break_case']

            break_context = BreakInvestigationContext(
                case_id=break_case.case_id,
                topology=break_case.topology,
                investigation_records=break_case.investigation_records,
                relaxed_segments=break_case.evidence.relaxed_segments
                if break_case.evidence
                else None,
            )

            return {
                'break_context': break_context,
                'evidence_trail': [],
                'gathered_evidence': [],
                'llm_round': 0,
                'llm_input_tokens': 0,
                'llm_output_tokens': 0,
                'tool_round': 0,
                'tool_calls_total': 0,
                'tool_cache': {},
            }

    # Node
    def _gather_evidence(self, state: BreakAnalysisGraphState) -> dict:
        with self._node_lifecycle('gather_evidence', state):
            analysis_run_id = state['analysis_run_id']
            case_id = short_id(state['break_case'].case_id)
            break_context = state['break_context']
            trail = state['evidence_trail']
            llm_round = state['llm_round'] + 1

            response, duration_ms = self._invoke_llm(
                self._llm_with_tools,
                [
                    SystemMessage(content=EVIDENCE_SYSTEM_PROMPT),
                    HumanMessage(content=str(break_context)),
                    *trail,
                ],
                analysis_run_id,
                case_id,
                llm_round,
            )

            if not isinstance(response, AIMessage):
                raise RuntimeError(
                    f'Expected an AIMessage from the tool-bound LLM, '
                    f'got {type(response).__name__}.'
                )

            input_tokens, output_tokens = self._log_llm_invocation(
                response,
                analysis_run_id,
                case_id,
                llm_round,
                duration_ms,
                tool_calls=len(response.tool_calls),
            )

            return {
                'evidence_trail': [*trail, response],
                'llm_round': llm_round,
                'llm_input_tokens': state['llm_input_tokens'] + (input_tokens or 0),
                'llm_output_tokens': state['llm_output_tokens'] + (output_tokens or 0),
            }

    # Node
    def _execute_tool_calls(self, state: BreakAnalysisGraphState) -> dict:
        with self._node_lifecycle('execute_tool_calls', state):
            break_case = state['break_case']
            analysis_run_id = state['analysis_run_id']
            case_id = short_id(break_case.case_id)
            response = state['evidence_trail'][-1]

            if state['tool_round'] >= self._max_tool_rounds:
                logger.error(
                    'Max tool rounds exceeded | analysis_run_id=%s | case_id=%s | '
                    'max_rounds=%s',
                    analysis_run_id,
                    case_id,
                    self._max_tool_rounds,
                )
                raise MaxToolRoundsError(
                    f'Maximum tool rounds exceeded for case '
                    f'{break_case.case_id}: {self._max_tool_rounds}'
                )

            if not isinstance(response, AIMessage):
                raise RuntimeError('The last message is not a valid AIMessage.')

            tool_round = state['tool_round'] + 1
            tool_cache = dict(state['tool_cache'])

            logger.info(
                'Tool round | analysis_run_id=%s | case_id=%s | round=%s | '
                'tool_calls=%s | tools=%s',
                analysis_run_id,
                case_id,
                tool_round,
                len(response.tool_calls),
                ','.join(tool_call['name'] for tool_call in response.tool_calls),
            )

            tool_results = []
            evidences = []
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool = self._tool_registry.get(tool_name)

                if tool is None:
                    logger.error(
                        'Unknown tool requested | analysis_run_id=%s | case_id=%s | '
                        'tool=%s',
                        analysis_run_id,
                        case_id,
                        tool_name,
                    )
                    raise UnknownToolError(
                        f'Unknown tool requested by agent: {tool_name}'
                    )

                tool_args = json.dumps(tool_call['args'], default=str)

                try:
                    key = self._tool_call_key(tool, tool_call)
                except ValidationError as exc:
                    logger.exception(
                        'Invalid tool arguments | analysis_run_id=%s | case_id=%s | '
                        'tool=%s | args=%s',
                        analysis_run_id,
                        case_id,
                        tool_name,
                        tool_args,
                    )
                    raise InvalidToolArgumentsError(
                        f"Invalid arguments for tool '{tool_name}' for case "
                        f'{break_case.case_id}'
                    ) from exc

                is_cached = key in tool_cache

                if is_cached:
                    result = tool_cache[key]
                    logger.debug(
                        'Tool cache hit | analysis_run_id=%s | case_id=%s | '
                        'tool=%s | args=%s',
                        analysis_run_id,
                        case_id,
                        tool_name,
                        tool_args,
                    )
                else:
                    tool_start = time.monotonic()
                    try:
                        result = self._invoke_tool_with_retry(
                            tool, tool_call['args'], analysis_run_id, case_id
                        )
                    except Exception as exc:
                        logger.exception(
                            'Tool failed | analysis_run_id=%s | case_id=%s | '
                            'tool=%s | args=%s',
                            analysis_run_id,
                            case_id,
                            tool_name,
                            tool_args,
                        )
                        if isinstance(exc, BreakAnalysisError):
                            raise
                        raise ToolExecutionError(
                            f"Tool '{tool_name}' failed for case {break_case.case_id}"
                        ) from exc

                    logger.info(
                        'Tool invoked | analysis_run_id=%s | case_id=%s | '
                        'tool=%s | args=%s | duration_ms=%s',
                        analysis_run_id,
                        case_id,
                        tool_name,
                        tool_args,
                        round((time.monotonic() - tool_start) * 1000),
                    )

                tool_results.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call['id'])
                )

                if is_cached:
                    continue

                tool_cache[key] = result
                evidences.append(
                    {
                        'tool_name': tool_name,
                        'tool_args': tool_call['args'],
                        'result': result,
                    }
                )

            return {
                'evidence_trail': [
                    *state['evidence_trail'],
                    *tool_results,
                ],
                'gathered_evidence': [
                    *state['gathered_evidence'],
                    *evidences,
                ],
                'tool_round': tool_round,
                'tool_calls_total': state['tool_calls_total']
                + len(response.tool_calls),
                'tool_cache': tool_cache,
            }

    # Node
    def _conclude(self, state: BreakAnalysisGraphState) -> dict:
        with self._node_lifecycle('conclude', state):
            break_case = state['break_case']
            analysis_run_id = state['analysis_run_id']
            case_id = short_id(break_case.case_id)
            evidence = state['gathered_evidence']
            llm_round = state['llm_round'] + 1

            response, duration_ms = self._invoke_llm(
                self._llm_with_structure,
                [
                    SystemMessage(content=CONCLUSION_SYSTEM_PROMPT),
                    HumanMessage(content=str(break_case)),
                    HumanMessage(
                        content=(
                            'Gathered evidence:\n'
                            + json.dumps(evidence, default=str, indent=2)
                        )
                    ),
                ],
                analysis_run_id,
                case_id,
                llm_round,
            )

            if not isinstance(response, dict):
                raise RuntimeError(
                    'Expected a dict from structured output with include_raw=True, '
                    f'got {type(response).__name__}.'
                )

            input_tokens, output_tokens = self._log_llm_invocation(
                response['raw'], analysis_run_id, case_id, llm_round, duration_ms
            )

            if response['parsing_error'] is not None:
                logger.error(
                    'Structured output parsing failed | analysis_run_id=%s | case_id=%s',
                    analysis_run_id,
                    case_id,
                )
                raise StructuredOutputError(
                    f'Failed to parse structured output for case {break_case.case_id}'
                ) from response['parsing_error']

            conclusion = response['parsed']

            result = BreakAnalysisResult(
                case_id=break_case.case_id,
                recon_result_ids=tuple(
                    record.recon_result_id for record in break_case.all_records
                ),
                status=conclusion.status,
                findings=conclusion.findings,
                explanation=conclusion.explanation,
            )

            return {
                'result': result,
                'llm_round': llm_round,
                'llm_input_tokens': state['llm_input_tokens'] + (input_tokens or 0),
                'llm_output_tokens': state['llm_output_tokens'] + (output_tokens or 0),
            }

    # Route
    def _route_after_evidence(self, state: BreakAnalysisGraphState) -> str:
        response = state['evidence_trail'][-1]

        if not isinstance(response, AIMessage):
            raise RuntimeError(
                'Expected the latest evidence message to be an AIMessage.'
            )

        if response.tool_calls:
            return 'execute_tool_calls'

        return 'conclude'

    # Helper
    @contextmanager
    def _node_lifecycle(
        self, node: str, state: BreakAnalysisGraphState
    ) -> Iterator[None]:
        analysis_run_id = state['analysis_run_id']
        case_id = short_id(state['break_case'].case_id)

        logger.info(
            'Graph node started | analysis_run_id=%s | case_id=%s | node=%s',
            analysis_run_id,
            case_id,
            node,
        )

        start = time.monotonic()
        try:
            yield
        except Exception as exc:
            # Lower-level handlers already log tracebacks; a ModelTransientError
            # may still be retried, and exhaustion is logged in invoke().
            logger.log(
                logging.WARNING
                if isinstance(exc, ModelTransientError)
                else logging.ERROR,
                'Graph node failed | analysis_run_id=%s | case_id=%s | node=%s | '
                'duration_ms=%s | error=%s',
                analysis_run_id,
                case_id,
                node,
                round((time.monotonic() - start) * 1000),
                type(exc).__name__,
            )
            raise

        logger.info(
            'Graph node completed | analysis_run_id=%s | case_id=%s | node=%s | '
            'duration_ms=%s',
            analysis_run_id,
            case_id,
            node,
            round((time.monotonic() - start) * 1000),
        )

    # Helper
    def _tool_call_key(self, tool: StructuredTool, tool_call: ToolCall) -> str:
        schema = tool.args_schema
        if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
            raise TypeError(f"Tool '{tool.name}' has no pydantic args_schema.")

        args = schema.model_validate(tool_call['args'])
        return json.dumps([tool.name, args.model_dump(mode='json')], sort_keys=True)

    # Helper
    def _invoke_llm(
        self,
        llm: Any,
        messages: list[BaseMessage],
        analysis_run_id: str,
        case_id: str,
        llm_round: int,
    ) -> tuple[Any, int]:
        logger.info(
            'Invoking LLM | analysis_run_id=%s | case_id=%s | round=%s',
            analysis_run_id,
            case_id,
            llm_round,
        )

        start = time.monotonic()
        try:
            response = llm.invoke(messages)
        except Exception as exc:
            if not self._model_provider.is_transient_error(exc):
                logger.exception(
                    'LLM invocation failed | analysis_run_id=%s | case_id=%s | '
                    'round=%s',
                    analysis_run_id,
                    case_id,
                    llm_round,
                )
                raise

            logger.warning(
                'LLM transient failure | analysis_run_id=%s | case_id=%s | round=%s',
                analysis_run_id,
                case_id,
                llm_round,
                exc_info=True,
            )
            raise ModelTransientError(
                f'Transient LLM failure for case {case_id}: {exc}'
            ) from exc

        return response, round((time.monotonic() - start) * 1000)

    # Helper
    def _invoke_tool_with_retry(
        self,
        tool: StructuredTool,
        tool_args: dict,
        analysis_run_id: str,
        case_id: str,
        max_attempts: int = 3,
    ) -> Any:
        if max_attempts < 1:
            raise ValueError('max_attempts must be at least 1.')

        for attempt in range(1, max_attempts + 1):
            try:
                return tool.invoke(tool_args)
            except ToolTransientError:
                if attempt == max_attempts:
                    raise

                delay_seconds = 2 ** (attempt - 1)
                logger.warning(
                    'Tool transient failure, retrying | analysis_run_id=%s | '
                    'case_id=%s | tool=%s | attempt=%s/%s | delay_s=%s',
                    analysis_run_id,
                    case_id,
                    tool.name,
                    attempt,
                    max_attempts,
                    delay_seconds,
                    exc_info=True,
                )
                time.sleep(delay_seconds)

    # Helper
    def _log_llm_invocation(
        self,
        message: BaseMessage,
        analysis_run_id: str,
        case_id: str,
        llm_round: int,
        duration_ms: int,
        tool_calls: int | None = None,
    ) -> tuple[int | None, int | None]:
        usage = getattr(message, 'usage_metadata', None) or {}
        input_tokens = usage.get('input_tokens')
        output_tokens = usage.get('output_tokens')

        # Ollama-specific timings, reported in nanoseconds.
        metadata = message.response_metadata or {}

        def ms(field: str) -> int:
            return round(metadata.get(field, 0) / 1_000_000)

        # Only tool-bound rounds carry a tool_calls field.
        tool_calls_field = '' if tool_calls is None else f' | tool_calls={tool_calls}'

        logger.info(
            'LLM invoked | analysis_run_id=%s | case_id=%s | round=%s%s | '
            'input_tokens=%s | output_tokens=%s | total_tokens=%s | '
            'prompt_eval_count=%s | eval_count=%s | load_ms=%s | '
            'prompt_eval_ms=%s | eval_ms=%s | total_ms=%s | duration_ms=%s',
            analysis_run_id,
            case_id,
            llm_round,
            tool_calls_field,
            input_tokens,
            output_tokens,
            usage.get('total_tokens'),
            metadata.get('prompt_eval_count'),
            metadata.get('eval_count'),
            ms('load_duration'),
            ms('prompt_eval_duration'),
            ms('eval_duration'),
            ms('total_duration'),
            duration_ms,
        )

        return input_tokens, output_tokens

    # Helper
    def _log_analysis_summary(self, state: dict, duration_ms: int) -> None:
        result = state['result']
        findings = result.findings if result else ()
        findings_by_cause = Counter(finding.root_cause for finding in findings)

        logger.info(
            'Break case analyzed | analysis_run_id=%s | case_id=%s | status=%s | '
            'findings=%s | findings_by_cause=%s | tool_rounds=%s | tool_calls=%s | '
            'unique_tool_calls=%s | llm_calls=%s | llm_input_tokens=%s | '
            'llm_output_tokens=%s | duration_ms=%s',
            state['analysis_run_id'],
            short_id(state['break_case'].case_id),
            result.status if result else None,
            len(findings),
            ', '.join(f'{cause}:{count}' for cause, count in findings_by_cause.items()),
            state['tool_round'],
            state['tool_calls_total'],
            len(state['tool_cache']),
            state['llm_round'],
            state['llm_input_tokens'],
            state['llm_output_tokens'],
            duration_ms,
        )
