from break_analysis import BreakAnalysisAgent

from evals.models import (
    EvalScenario,
    EvalRunResult,
    EvalGrade,
)
from evals.fake_tools import (
    FakeAtlasTools,
    FakeRegistryTools
)
from evals.graders import grade_scenario
from evals.fixtures import ToolFixtureStore


class EvalRunner:
    def __init__(self, llm):
        self._llm = llm


    def run(
        self,
        scenario: EvalScenario,
    ) -> EvalRunResult:
        store = ToolFixtureStore(scenario.tool_fixtures)

        agent = BreakAnalysisAgent(
            llm=self._llm,
            registry_tools=FakeRegistryTools(store),
            atlas_tools=FakeAtlasTools(store),
        )

        try:
            result = agent.analyze(scenario.break_case)
        except Exception as exc:
            return EvalRunResult(
                scenario_name=scenario.name,
                grade=EvalGrade(
                    passed=False,
                    failures=(str(exc),),
                ),
                result=None,
                calls=store.calls,
                error=str(exc),
            )

        grade = grade_scenario(
            scenario=scenario,
            result=result,
            calls=store.calls,
        )

        return EvalRunResult(
            scenario_name=scenario.name,
            grade=grade,
            result=result,
            calls=store.calls,
        )
