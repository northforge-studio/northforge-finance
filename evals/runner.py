from break_analysis import BreakAnalysisAgent
from break_analysis.model_provider import ChatModelProvider
from evals.fake_tools import FakeAtlasTools, FakeRegistryTools
from evals.fixtures import ToolFixtureStore
from evals.graders import grade_scenario
from evals.models import (
    EvalGrade,
    EvalRunResult,
    EvalScenario,
)


class EvalRunner:
    def __init__(self, model_provider: ChatModelProvider):
        self._model_provider = model_provider

    def run(
        self,
        scenario: EvalScenario,
    ) -> EvalRunResult:
        store = ToolFixtureStore(scenario.tool_fixtures)

        agent = BreakAnalysisAgent(
            model_provider=self._model_provider,
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
