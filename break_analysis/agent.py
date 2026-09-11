from langchain_core.tools import StructuredTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage

from break_analysis.prompts import SYSTEM_PROMPT
from break_analysis.tools import RegistryTools, ValidateSegmentInput
from break_analysis.models import (
    BreakCase,
    BreakAnalysisResult,
    BreakAnalysisConclusion
)


class BreakAnalysisAgent:
    def __init__(
        self,
        llm: BaseChatModel,
        registry_tools: RegistryTools,
        max_tool_rounds: int = 10
    ):
        if max_tool_rounds < 1:
            raise ValueError('max_tool_rounds must be at least 1.')

        self._llm = llm
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
            )
        ]

        self._llm_with_tools = llm.bind_tools(self._tools)
        self._tool_registry = {tool.name: tool for tool in self._tools}

        self._llm_with_structure = llm.with_structured_output(BreakAnalysisConclusion.model_json_schema())


    def analyze(
        self,
        break_case: BreakCase
    ) -> BreakAnalysisResult:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=str(break_case))
        ]

        response = self._llm_with_tools.invoke(messages)

        tool_round = 0
        tool_cache: dict[tuple, object] = {}

        while response.tool_calls:
            if tool_round >= self._max_tool_rounds:
                raise RuntimeError(
                    f'Maximum tool rounds exceeded for case '
                    f'{break_case.case_id}: {self._max_tool_rounds}'
                )

            tool_round += 1
            messages.append(response)

            for tool_call in response.tool_calls:
                key = self._tool_call_key(tool_call)
                if key in tool_cache:
                    result = tool_cache[key]
                else:
                    tool_name = tool_call['name']
                    tool = self._tool_registry.get(tool_name)

                    if tool is None:
                        raise RuntimeError(
                            f'Unknown tool requested by agent: {tool_name}'
                        )

                    try:
                        result = tool.invoke(tool_call['args'])
                    except Exception as exc:
                        raise RuntimeError(
                            f'Tool \'{tool_name}\' failed for case '
                            f'{break_case.case_id}'
                        ) from exc

                    tool_cache[key] = result

                messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call['id']
                    )
                )

            response = self._llm_with_tools.invoke(messages)

        conclusion_raw = self._llm_with_structure.invoke(messages)
        conclusion = BreakAnalysisConclusion.model_validate(conclusion_raw)

        return BreakAnalysisResult(
            case_id=break_case.case_id,
            recon_result_ids=tuple(record.recon_result_id for record in break_case.all_records),
            status=conclusion.status,
            root_cause=conclusion.root_cause,
            explanation=conclusion.explanation
        )


    def _tool_call_key(self, tool_call: dict) -> tuple:
        return (
            tool_call['name'],
            tuple(sorted(tool_call['args'].items()))
        )
