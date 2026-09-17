from uuid import UUID
from enum import StrEnum
from datetime import date
from decimal import Decimal
from dataclasses import dataclass

from pydantic import BaseModel

from gl.models import GLSegments
from registry.models import GLSegmentType
from atlas.models import MappingResolutionEvidence


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
    INTERFACE_ONLY = 'INTERFACE_ONLY'
    GL_ONLY = 'GL_ONLY'
    AMBIGUOUS = 'AMBIGUOUS'
    UNMATCHED = 'UNMATCHED'


@dataclass(frozen=True)
class BreakInvestigationContext:
    case_id: UUID
    topology: BreakTopology
    investigation_records: tuple[BreakRecord, ...]
    relaxed_segments: tuple[GLSegmentType, ...] | None


@dataclass(frozen=True)
class BreakCaseEvidence:
    relaxed_segments: tuple[GLSegmentType, ...]


@dataclass(frozen=True)
class BreakCase:
    case_id: UUID
    topology: BreakTopology

    investigation_records: tuple[BreakRecord, ...]
    pivot: BreakRecord | None = None
    evidence: BreakCaseEvidence | None = None


    def __post_init__(self):
        if not self.investigation_records:
            raise ValueError(
                'BreakCase must contain at least one investigation record.'
            )

        pivot_topologies = {
            BreakTopology.ONE_TO_ONE,
            BreakTopology.MANY_TO_ONE
        }

        if self.topology in pivot_topologies and self.pivot is None:
            raise ValueError(
                f'{self.topology} requires a pivot.'
            )

        if self.topology not in pivot_topologies and self.pivot is not None:
            raise ValueError(
                f'{self.topology} must not have a pivot.'
            )

        if (
            self.topology == BreakTopology.ONE_TO_ONE
            and len(self.investigation_records) != 1
        ):
            raise ValueError(
                'ONE_TO_ONE requires exactly one investigation record.'
            )

        if (
            self.topology == BreakTopology.MANY_TO_ONE
            and len(self.investigation_records) < 2
        ):
            raise ValueError(
                'MANY_TO_ONE requires at least two investigation records.'
            )

        if (
            self.pivot is not None
            and any(
                record.recon_result_id == self.pivot.recon_result_id
                for record in self.investigation_records
            )
        ):
            raise ValueError(
                'Pivot cannot also be an investigation record.'
            )


    @property
    def all_records(self) -> tuple[BreakRecord, ...]:
        if self.pivot is None:
            return self.investigation_records

        return (
            self.pivot,
            *self.investigation_records
        )


@dataclass(frozen=True)
class BreakPartitionKey:
    as_of_date: date
    entity_cd: str
    source_cd: str
    accounted_currency: str


@dataclass(frozen=True)
class FoundryMappingInputValues:
    values: dict[str, str]
    source_record_count: int


@dataclass(frozen=True)
class AtlasInputResolution:
    foundry_inputs: FoundryMappingInputValues
    resolution: MappingResolutionEvidence


@dataclass(frozen=True)
class AtlasResolutionEvidence:
    recon_result_id: UUID
    segment_type: GLSegmentType
    mapping_name: str
    input_resolutions: tuple[AtlasInputResolution, ...]
