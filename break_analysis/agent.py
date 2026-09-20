import json
import time
from collections import Counter

from langchain_core.tools import StructuredTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, SystemMessage

from core.logging import get_logger, short_id

from break_analysis.prompts import EVIDENCE_SYSTEM_PROMPT, CONCLUSION_SYSTEM_PROMPT
from break_analysis.tools.registry import RegistryTools, ValidateSegmentInput
from break_analysis.tools.atlas import AtlasTools, InvestigateAtlasResolutionInput
from break_analysis.models import (
    BreakCase,
    BreakAnalysisResult,
    BreakAnalysisConclusion,
    BreakInvestigationContext
)


logger = get_logger(__name__)


class BreakAnalysisAgent:
    def __init__(
        self,
        llm: BaseChatModel,
        atlas_tools: AtlasTools,
        registry_tools: RegistryTools,
        max_tool_rounds: int = 10
    ):
        if max_tool_rounds < 1:
            raise ValueError('max_tool_rounds must be at least 1.')

        self._llm = llm
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
                args_schema=ValidateSegmentInput
            ),
            StructuredTool.from_function(
                func=self._registry_tools.get_segment_details,
                name='get_segment_details',
                description=(
                    'Retrieve the details of a GL segment value from the Registry, '
                    'including its existence and status.'
                ),
                args_schema=ValidateSegmentInput
            ),
            StructuredTool.from_function(
                func=self._atlas_tools.investigate_resolution,
                name='investigate_resolution',
                description=(
                    'Investigate why a blank or unresolved GL segment value '
                    'failed to resolve through Atlas mapping.'
                ),
                args_schema=InvestigateAtlasResolutionInput
            )
        ]

        self._llm_with_tools = llm.bind_tools(self._tools, reasoning=False)
        self._tool_registry = {tool.name: tool for tool in self._tools}

        self._llm_with_structure = llm.with_structured_output(
            BreakAnalysisConclusion,
            method='json_schema',
            include_raw=True
        )


    def analyze(
        self,
        break_case: BreakCase
    ) -> BreakAnalysisResult:
        start = time.monotonic()
        case_id = short_id(break_case.case_id)
        workflow_run_id = short_id(break_case.all_records[0].workflow_run_id)

        logger.info(
            'Analyzing break case | case_id=%s | workflow_run_id=%s | '
            'topology=%s | records=%s',
            case_id, workflow_run_id,
            break_case.topology, len(break_case.all_records)
        )

        break_context = BreakInvestigationContext(
            case_id=break_case.case_id,
            topology=break_case.topology,
            investigation_records=break_case.investigation_records,
            relaxed_segments=break_case.evidence.relaxed_segments if break_case.evidence else None
        )

        messages: list[BaseMessage] = []

        llm_round = 0
        llm_input_tokens = 0
        llm_output_tokens = 0

        llm_round += 1
        response, input_tokens, output_tokens = self._invoke_with_tools(
            [
                SystemMessage(content=EVIDENCE_SYSTEM_PROMPT),
                HumanMessage(content=str(break_context)),
                *messages
            ],
            case_id,
            llm_round
        )
        llm_input_tokens += input_tokens or 0
        llm_output_tokens += output_tokens or 0

        tool_round = 0
        tool_calls_total = 0
        tool_cache: dict[tuple, object] = {}

        while response.tool_calls:
            if tool_round >= self._max_tool_rounds:
                logger.error(
                    'Max tool rounds exceeded | case_id=%s | max_rounds=%s',
                    case_id, self._max_tool_rounds
                )
                raise RuntimeError(
                    f'Maximum tool rounds exceeded for case '
                    f'{break_case.case_id}: {self._max_tool_rounds}'
                )

            tool_round += 1
            messages.append(response)

            logger.info(
                'Tool round | case_id=%s | round=%s | tool_calls=%s',
                case_id, tool_round, len(response.tool_calls)
            )

            for tool_call in response.tool_calls:
                tool_calls_total += 1
                tool_name = tool_call['name']
                key = self._tool_call_key(tool_call)

                if key in tool_cache:
                    result = tool_cache[key]
                    logger.debug(
                        'Tool cache hit | case_id=%s | tool=%s | args=%s',
                        case_id, tool_name,
                        json.dumps(tool_call['args'], default=str)
                    )
                else:
                    tool = self._tool_registry.get(tool_name)

                    if tool is None:
                        logger.error(
                            'Unknown tool requested | case_id=%s | tool=%s',
                            case_id, tool_name
                        )
                        raise RuntimeError(
                            f'Unknown tool requested by agent: {tool_name}'
                        )

                    tool_start = time.monotonic()
                    try:
                        result = tool.invoke(tool_call['args'])
                    except Exception as exc:
                        logger.exception(
                            'Tool failed | case_id=%s | tool=%s',
                            case_id, tool_name
                        )
                        raise RuntimeError(
                            f'Tool \'{tool_name}\' failed for case '
                            f'{break_case.case_id}'
                        ) from exc

                    tool_duration_ms = round((time.monotonic() - tool_start) * 1000)
                    logger.info(
                        'Tool invoked | case_id=%s | tool=%s | args=%s | '
                        'duration_ms=%s',
                        case_id, tool_name,
                        json.dumps(tool_call['args'], default=str),
                        tool_duration_ms
                    )

                    tool_cache[key] = result

                messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call['id']
                    )
                )

            llm_round += 1
            response, input_tokens, output_tokens = self._invoke_with_tools(
                [
                    SystemMessage(content=EVIDENCE_SYSTEM_PROMPT),
                    HumanMessage(content=str(break_context)),
                    *messages
                ],
                case_id,
                llm_round
            )
            llm_input_tokens += input_tokens or 0
            llm_output_tokens += output_tokens or 0

        llm_round += 1
        structured_result, input_tokens, output_tokens = self._invoke_structured(
            [
                SystemMessage(content=CONCLUSION_SYSTEM_PROMPT),
                HumanMessage(content=str(break_case)),
                *messages
            ],
            case_id,
            llm_round
        )
        llm_input_tokens += input_tokens or 0
        llm_output_tokens += output_tokens or 0

        if structured_result['parsing_error'] is not None:
            logger.error(
                'Structured output parsing failed | case_id=%s',
                case_id
            )
            raise RuntimeError(
                f'Failed to parse structured output for case '
                f'{break_case.case_id}'
            ) from structured_result['parsing_error']

        conclusion = structured_result['parsed']

        duration_ms = round((time.monotonic() - start) * 1000)

        finding_causes = Counter(
            finding.root_cause for finding in conclusion.findings
        )
        finding_causes_summary = ', '.join(
            f'{root_cause}:{count}'
            for root_cause, count in finding_causes.items()
        )

        logger.info(
            'Break case analyzed | case_id=%s | status=%s | findings=%s | '
            'findings_by_cause=%s | tool_rounds=%s | tool_calls=%s | '
            'unique_tool_calls=%s | llm_calls=%s | llm_input_tokens=%s | '
            'llm_output_tokens=%s | duration_ms=%s',
            case_id,
            conclusion.status,
            len(conclusion.findings),
            finding_causes_summary,
            tool_round,
            tool_calls_total,
            len(tool_cache),
            llm_round,
            llm_input_tokens,
            llm_output_tokens,
            duration_ms,
        )

        return BreakAnalysisResult(
            case_id=break_case.case_id,
            recon_result_ids=tuple(record.recon_result_id for record in break_case.all_records),
            status=conclusion.status,
            findings=conclusion.findings,
            explanation=conclusion.explanation
        )


    def _tool_call_key(self, tool_call: dict) -> tuple:
        return (
            tool_call['name'],
            tuple(sorted(tool_call['args'].items()))
        )


    def _invoke_with_tools(self, messages: list, case_id, llm_round: int) -> tuple:
        logger.info(
            'Invoking LLM | case_id=%s | round=%s',
            case_id, llm_round
        )

        start = time.monotonic()
        response = self._llm_with_tools.invoke(messages)
        duration_ms = round((time.monotonic() - start) * 1000)

        usage = getattr(response, 'usage_metadata', None) or {}
        input_tokens = usage.get('input_tokens')
        output_tokens = usage.get('output_tokens')
        total_tokens = usage.get('total_tokens')

        response_metadata = getattr(response, 'response_metadata', None) or {}
        load_ms = round(response_metadata.get('load_duration', 0) / 1_000_000)
        prompt_eval_ms = round(
            response_metadata.get('prompt_eval_duration', 0) / 1_000_000
        )
        eval_ms = round(response_metadata.get('eval_duration', 0) / 1_000_000)
        total_ms = round(response_metadata.get('total_duration', 0) / 1_000_000)
        prompt_eval_count = response_metadata.get('prompt_eval_count')
        eval_count = response_metadata.get('eval_count')

        logger.info(
            'LLM invoked | case_id=%s | round=%s | tool_calls=%s | '
            'input_tokens=%s | output_tokens=%s | total_tokens=%s | '
            'prompt_eval_count=%s | eval_count=%s | load_ms=%s | '
            'prompt_eval_ms=%s | eval_ms=%s | total_ms=%s | duration_ms=%s',
            case_id, llm_round, len(response.tool_calls), input_tokens,
            output_tokens, total_tokens, prompt_eval_count, eval_count,
            load_ms, prompt_eval_ms, eval_ms, total_ms, duration_ms
        )

        return response, input_tokens, output_tokens


    def _invoke_structured(self, messages: list, case_id, llm_round: int) -> tuple:
        logger.info(
            'Invoking LLM | case_id=%s | round=%s',
            case_id, llm_round
        )

        start = time.monotonic()
        structured_result = self._llm_with_structure.invoke(messages)
        duration_ms = round((time.monotonic() - start) * 1000)

        raw = structured_result['raw']
        usage = getattr(raw, 'usage_metadata', None) or {}
        input_tokens = usage.get('input_tokens')
        output_tokens = usage.get('output_tokens')
        total_tokens = usage.get('total_tokens')

        response_metadata = getattr(raw, 'response_metadata', None) or {}
        load_ms = round(response_metadata.get('load_duration', 0) / 1_000_000)
        prompt_eval_ms = round(
            response_metadata.get('prompt_eval_duration', 0) / 1_000_000
        )
        eval_ms = round(response_metadata.get('eval_duration', 0) / 1_000_000)
        total_ms = round(response_metadata.get('total_duration', 0) / 1_000_000)
        prompt_eval_count = response_metadata.get('prompt_eval_count')
        eval_count = response_metadata.get('eval_count')

        logger.info(
            'LLM invoked | case_id=%s | round=%s | input_tokens=%s | '
            'output_tokens=%s | total_tokens=%s | prompt_eval_count=%s | '
            'eval_count=%s | load_ms=%s | prompt_eval_ms=%s | eval_ms=%s | '
            'total_ms=%s | duration_ms=%s',
            case_id, llm_round, input_tokens, output_tokens, total_tokens,
            prompt_eval_count, eval_count, load_ms, prompt_eval_ms, eval_ms,
            total_ms, duration_ms
        )

        return structured_result, input_tokens, output_tokens
