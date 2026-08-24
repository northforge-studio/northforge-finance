from enum import StrEnum
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


class RunStatus(StrEnum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'


@dataclass(frozen=True)
class WorkflowRun:
    workflow_run_id: UUID
    dataclass: str
    business_dt: date
    batch_id: str | None
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class ExecutionRun:
    run_id: UUID
    workflow_run_id: UUID
    parent_run_id: UUID | None
    component: str
    operation: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None
    retry_of_run_id: UUID | None


@dataclass(frozen=True)
class RunDependency:
    consumer_run_id: UUID
    producer_run_id: UUID
    input_role: str | None = None


@dataclass(frozen=True)
class RunIdentity:
    workflow_run_id: UUID
    run_id: UUID
    parent_run_id: UUID | None


@dataclass(frozen=True)
class ZoneResult:
    identity: RunIdentity
    zone: str
    status: RunStatus
    record_count: int


@dataclass(frozen=True)
class PipelineResult:
    identity: RunIdentity
    status: RunStatus
    zones: tuple[ZoneResult, ...]
