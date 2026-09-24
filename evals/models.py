from uuid import UUID
from typing import Any
from dataclasses import dataclass

from break_analysis.models import (
    BreakCase,
    RootCause,
    BreakAnalysisResult,
    BreakAnalysisStatus
)

from gl.models import GLSegmentType


@dataclass(frozen=True)
class ToolFixture:
    tool_name: str
    args: dict[str, Any]
    result: object


@dataclass(frozen=True)
class ToolCallRecord:
    tool_name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class ExpectedFinding:
    root_cause: RootCause
    
    recon_result_id: UUID
    segment_type: GLSegmentType
    segment_value: str


@dataclass(frozen=True)
class EvalExpectation:
    status: BreakAnalysisStatus
    findings: tuple[ExpectedFinding, ...]

    required_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalScenario:
    name: str
    description: str

    break_case: BreakCase
    tool_fixtures: tuple[ToolFixture, ...]

    expected: EvalExpectation


@dataclass(frozen=True)
class EvalGrade:
    passed: bool
    failures: tuple[str, ...]


@dataclass(frozen=True)
class EvalRunResult:
    scenario_name: str
    grade: EvalGrade
    result: BreakAnalysisResult | None
    calls: tuple[ToolCallRecord, ...]
    error: str | None = None
