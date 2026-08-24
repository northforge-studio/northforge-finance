from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from core.runs.models import RunStatus, WorkflowRun, ExecutionRun, RunDependency
from core.runs.repository import RunRepository


class RunTracker:
    def __init__(self, repository: RunRepository):
        self._repository = repository


    def start_workflow(
        self,
        *,
        dataclass: str,
        business_dt: date,
        batch_id: str | None = None,
    ) -> WorkflowRun:
        run = WorkflowRun(
            workflow_run_id=uuid4(),
            dataclass=dataclass,
            business_dt=business_dt,
            batch_id=batch_id,
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
        )
        self._repository.create_workflow_run(run)

        return run


    def start_execution(
        self,
        *,
        workflow_run_id: UUID,
        component: str,
        operation: str,
        parent_run_id: UUID | None = None,
        retry_of_run_id: UUID | None = None,
    ) -> ExecutionRun:
        run = ExecutionRun(
            run_id=uuid4(),
            workflow_run_id=workflow_run_id,
            parent_run_id=parent_run_id,
            component=component,
            operation=operation,
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            retry_of_run_id=retry_of_run_id,
        )
        self._repository.create_execution_run(run)

        return run


    def complete_workflow(self, workflow_run_id: UUID) -> None:
        self._repository.update_workflow_status(
            workflow_run_id,
            RunStatus.SUCCEEDED,
            completed_at=datetime.now(timezone.utc),
        )


    def fail_workflow(self, workflow_run_id: UUID) -> None:
        self._repository.update_workflow_status(
            workflow_run_id,
            RunStatus.FAILED,
            completed_at=datetime.now(timezone.utc),
        )


    def complete_execution(self, run_id: UUID) -> None:
        self._repository.update_execution_status(
            run_id,
            RunStatus.SUCCEEDED,
            completed_at=datetime.now(timezone.utc),
        )


    def fail_execution(self, run_id: UUID) -> None:
        self._repository.update_execution_status(
            run_id,
            RunStatus.FAILED,
            completed_at=datetime.now(timezone.utc),
        )


    def add_dependency(
        self,
        *,
        consumer_run_id: UUID,
        producer_run_id: UUID,
        input_role: str | None = None,
    ) -> None:
        self._repository.create_dependency(
            RunDependency(
                consumer_run_id=consumer_run_id,
                producer_run_id=producer_run_id,
                input_role=input_role,
            )
        )
