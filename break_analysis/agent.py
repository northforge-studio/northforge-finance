from break_analysis.prompts import SYSTEM_PROMPT
from break_analysis.tools import RegistryTools, ValidateSegmentInput
from break_analysis.models import (
    BreakCase, 
    BreakAnalysisResult, 
    BreakAnalysisConclusion
)

from langchain_core.tools import StructuredTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage


class BreakAnalysisAgent:
    def __init__(
        self,
        llm: BaseChatModel,
        registry_tools: RegistryTools,
    ):
        self._llm = llm
        self._registry_tools = registry_tools

        self._tools = [
            StructuredTool.from_function(
                func=self._registry_tools.validate_segment,
                name='validate_segment',
                description=(
                    'Validate whether a GL segment value is active '
                    'and valid in Registry.'
                ),
                args_schema=ValidateSegmentInput,
            )
        ]

        self._llm_with_tools = llm.bind_tools(self._tools)
        self._tool_registry = {tool.name: tool for tool in self._tools}

        self._llm_with_structure = llm.with_structured_output(BreakAnalysisConclusion.model_json_schema())


    def analyze(
        self,
        break_case: BreakCase,
    ) -> BreakAnalysisResult:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=str(break_case)),
        ]

        response = self._llm_with_tools.invoke(messages)

        while response.tool_calls:
            messages.append(response)

            for tool_call in response.tool_calls:
                tool = self._tool_registry[tool_call['name']]
                result = tool.invoke(tool_call['args'])

                messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call['id'],
                    )
                )

            response = self._llm_with_tools.invoke(messages)

        conclusion_raw = self._llm_with_structure.invoke(messages)
        conclusion = BreakAnalysisConclusion.model_validate(conclusion_raw)

        return BreakAnalysisResult(
            case_id=break_case.case_id,
            recon_result_ids=tuple(record.recon_result_id for record in break_case.records),
            status=conclusion.status,
            root_cause=conclusion.root_cause,
            explanation=conclusion.explanation,
        )
