import json
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
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
from pydantic import BaseModel

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


class BreakAnalysisGraphInput(TypedDict):
    break_case: BreakCase


class BreakAnalysisGraphOutput(TypedDict):
    result: BreakAnalysisResult | None


class GatheredEvidence(TypedDict):
    tool_name: str
    tool_args: dict
    result: object


class BreakAnalysisGraphState(TypedDict):
    break_case: BreakCase
    result: BreakAnalysisResult | None

    break_context: BreakInvestigationContext | None

    evidence_trail: list[BaseMessage]
    gathered_evidence: list[GatheredEvidence]

    # llm_round: int
    # llm_input_tokens: int
    # llm_output_tokens: int

    tool_round: int
    tool_calls_total: int
    tool_cache: dict[str, object]


class BreakAnalysisGraph:
    def __init__(
        self,
        llm: BaseChatModel,
        atlas_tools: AtlasToolsProtocol,
        registry_tools: RegistryToolsProtocol,
        max_tool_rounds: int = 10,
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
        final_state = self._graph.invoke(graph_input)

        return BreakAnalysisGraphOutput(result=final_state['result'])

    def _build(self):
        graph = StateGraph(
            BreakAnalysisGraphState, input_schema=BreakAnalysisGraphInput
        )

        graph.add_node('initialize_analysis', self._initialize_analysis)
        graph.add_node('gather_evidence', self._gather_evidence)
        graph.add_node('execute_tool_calls', self._execute_tool_calls)
        graph.add_node('conclude', self._conclude)

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
            'tool_round': 0,
            'tool_calls_total': 0,
            'tool_cache': {},
        }

    # Node
    def _gather_evidence(self, state: BreakAnalysisGraphState) -> dict:
        break_context = state['break_context']
        trail = state['evidence_trail']

        response = self._llm_with_tools.invoke(
            [
                SystemMessage(content=EVIDENCE_SYSTEM_PROMPT),
                HumanMessage(content=str(break_context)),
                *trail,
            ]
        )

        return {
            'evidence_trail': [*trail, response],
        }

    # Node
    def _execute_tool_calls(self, state: BreakAnalysisGraphState) -> dict:
        break_case = state['break_case']
        response = state['evidence_trail'][-1]

        if state['tool_round'] >= self._max_tool_rounds:
            raise RuntimeError(
                f'Maximum tool rounds exceeded for case '
                f'{break_case.case_id}: {self._max_tool_rounds}'
            )

        if not isinstance(response, AIMessage):
            raise RuntimeError('The last message is not a valid AIMessage.')

        tool_cache = dict(state['tool_cache'])

        tool_results = []
        evidences = []
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool = self._tool_registry.get(tool_name)

            if tool is None:
                raise RuntimeError(f'Unknown tool requested by agent: {tool_name}')

            try:
                key = self._tool_call_key(tool, tool_call)
                is_cached = key in tool_cache
                result = (
                    tool_cache[key] if is_cached else tool.invoke(tool_call['args'])
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Tool '{tool_name}' failed for case {break_case.case_id}"
                ) from exc

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
            'tool_round': state['tool_round'] + 1,
            'tool_calls_total': state['tool_calls_total'] + len(response.tool_calls),
            'tool_cache': tool_cache,
        }

    # Node
    def _conclude(self, state: BreakAnalysisGraphState) -> dict:
        break_case = state['break_case']
        evidence = state['gathered_evidence']

        response = self._llm_with_structure.invoke(
            [
                SystemMessage(content=CONCLUSION_SYSTEM_PROMPT),
                HumanMessage(content=str(break_case)),
                HumanMessage(
                    content=(
                        'Gathered evidence:\n'
                        + json.dumps(evidence, default=str, indent=2)
                    )
                ),
            ]
        )

        if not isinstance(response, dict):
            raise RuntimeError(
                'Expected a dict from structured output with include_raw=True, '
                f'got {type(response).__name__}.'
            )

        if response['parsing_error'] is not None:
            raise RuntimeError(
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
    def _tool_call_key(self, tool: StructuredTool, tool_call: ToolCall) -> str:
        schema = tool.args_schema
        if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
            raise TypeError(f"Tool '{tool.name}' has no pydantic args_schema.")

        args = schema.model_validate(tool_call['args'])
        return json.dumps([tool.name, args.model_dump(mode='json')], sort_keys=True)
