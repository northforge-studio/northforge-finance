from uuid import UUID
from enum import StrEnum
from datetime import date
from decimal import Decimal
from dataclasses import dataclass

from pydantic import BaseModel

from gl.models import GLSegments


class BreakAnalysisStatus(StrEnum):
    EXPLAINED = 'EXPLAINED'
    UNEXPLAINED = 'UNEXPLAINED'


class RootCause(StrEnum):
    REGISTRY_INVALID_SEGMENT = 'REGISTRY_INVALID_SEGMENT'


@dataclass(frozen=True)
class BreakRecord:
    recon_result_id: UUID
    workflow_run_id: UUID

    as_of_date: date

    segments: GLSegments

    accounted_currency: str

    interface_balance: Decimal
    gl_balance: Decimal
    difference_amount: Decimal


class BreakAnalysisConclusion(BaseModel):
    status: BreakAnalysisStatus
    root_cause: RootCause | None
    explanation: str


class BreakAnalysisResult(BaseModel):
    recon_result_id: UUID

    status: BreakAnalysisStatus
    root_cause: RootCause | None
    explanation: str
