from uuid import UUID
from enum import StrEnum
from datetime import date
from decimal import Decimal
from dataclasses import dataclass

from pydantic import BaseModel

from gl.models import GLSegments
from registry.models import GLSegmentType


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
    case_id: UUID
    recon_result_ids: tuple[UUID, ...]

    status: BreakAnalysisStatus
    root_cause: RootCause | None
    explanation: str


class BreakTopology(StrEnum):
    ONE_TO_ONE = 'ONE_TO_ONE'
    MANY_TO_ONE = 'MANY_TO_ONE'
    ONE_TO_MANY = 'ONE_TO_MANY'
    MANY_TO_MANY = 'MANY_TO_MANY'
    INTERFACE_ONLY = 'INTERFACE_ONLY'
    GL_ONLY = 'GL_ONLY'
    AMBIGUOUS = 'AMBIGUOUS'
    UNMATCHED = 'UNMATCHED'


@dataclass(frozen=True)
class BreakCaseEvidence:
    relaxed_segments: tuple[GLSegmentType, ...]


@dataclass(frozen=True)
class BreakCase:
    case_id: UUID
    topology: BreakTopology
    records: tuple[BreakRecord, ...]
    evidence: BreakCaseEvidence | None = None


@dataclass(frozen=True)
class BreakPartitionKey:
    as_of_date: date
    entity_cd: str
    source_cd: str
    accounted_currency: str
