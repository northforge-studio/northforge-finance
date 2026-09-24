from typing import Any
from dataclasses import dataclass

from evals.models import ToolFixture


@dataclass(frozen=True)
class ToolCallRecord:
    tool_name: str
    args: dict[str, Any]


class ToolFixtureStore:
    def __init__(
        self,
        fixtures: tuple[ToolFixture, ...],
    ):
        self._fixtures = fixtures
        self._calls: list[ToolCallRecord] = []


    @property
    def calls(self) -> tuple[ToolCallRecord, ...]:
        return tuple(self._calls)


    def get_result(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> object:
        self._calls.append(
            ToolCallRecord(
                tool_name=tool_name,
                args=args,
            )
        )

        matches = [
            fixture
            for fixture in self._fixtures
            if (
                fixture.tool_name == tool_name
                and fixture.args == args
            )
        ]

        if not matches:
            raise AssertionError(
                f'Unexpected tool call: {tool_name} {args}'
            )

        if len(matches) > 1:
            raise AssertionError(
                f'Duplicate tool fixtures found for: {tool_name} {args}'
            )

        return matches[0].result
