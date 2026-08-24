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
