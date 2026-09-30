from break_analysis.graph import BreakAnalysisGraph
from break_analysis.model_provider import ChatModelProvider
from break_analysis.models import BreakAnalysisResult, BreakCase
from break_analysis.tools.atlas import AtlasToolsProtocol
from break_analysis.tools.registry import RegistryToolsProtocol


class BreakAnalysisAgent:
    def __init__(
        self,
        model_provider: ChatModelProvider,
        atlas_tools: AtlasToolsProtocol,
        registry_tools: RegistryToolsProtocol,
        max_tool_rounds: int = 10,
    ):
        self._graph = BreakAnalysisGraph(
            model_provider=model_provider,
            atlas_tools=atlas_tools,
            registry_tools=registry_tools,
            max_tool_rounds=max_tool_rounds,
        )

    def analyze(self, break_case: BreakCase) -> BreakAnalysisResult:
        state = self._graph.invoke({'break_case': break_case})

        if state['result'] is None:
            raise RuntimeError('Break analysis graph completed without a result.')

        return state['result']
