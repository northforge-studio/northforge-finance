from uuid import UUID
from typing import Any
from dataclasses import dataclass

from break_analysis.models import (
    BreakCase,
    RootCause,
    BreakAnalysisStatus
)

from gl.models import GLSegmentType


@dataclass(frozen=True)
class ToolFixture:
    tool_name: str
    args: dict[str, Any]
    result: object


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
    