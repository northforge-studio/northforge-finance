from dataclasses import dataclass

from core.runs.models import PipelineResult
from gl.models import GLImportResult


@dataclass(frozen=True)
class WorkflowResult:
    foundry: PipelineResult
    gl: GLImportResult
