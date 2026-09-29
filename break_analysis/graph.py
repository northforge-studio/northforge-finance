from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from break_analysis.models import BreakAnalysisResult, BreakCase


class BreakAnalysisGraphState(TypedDict):
    break_case: BreakCase
    result: BreakAnalysisResult | None


class BreakAnalysisGraph:
    def __init__(self, run_v1_analysis: Callable[[BreakCase], BreakAnalysisResult]):
        self._run_v1_analysis = run_v1_analysis
        self._graph = self._build()

    def invoke(self, state: BreakAnalysisGraphState) -> BreakAnalysisGraphState:
        final_state = self._graph.invoke(state)

        return BreakAnalysisGraphState(
            break_case=final_state['break_case'],
            result=final_state['result'],
        )

    def _build(self) -> CompiledStateGraph:
        graph = StateGraph(BreakAnalysisGraphState)

        graph.add_node('run_analysis', self._run_analysis)

        graph.add_edge(START, 'run_analysis')
        graph.add_edge('run_analysis', END)

        return graph.compile()

    # Node
    def _run_analysis(self, state: BreakAnalysisGraphState) -> dict:
        result = self._run_v1_analysis(state['break_case'])

        return {'result': result}
