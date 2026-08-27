from datetime import datetime
from uuid import UUID

from core.db import PostgresConfig, PostgresExecutor

from core.runs.models import (
    RunStatus,
    WorkflowRun,
    ExecutionRun,
    RunDependency,
    WorkflowRunSummary,
)


class RunRepository:
    def __init__(self):
        self._config = PostgresConfig.from_env()
        self._executor = PostgresExecutor(self._config)


    def create_workflow_run(self, run: WorkflowRun) -> None:
        self._executor.execute(
            '''
            INSERT INTO core.workflow_run (
                workflow_run_id, dataclass, business_dt,
                status, started_at, completed_at
            ) VALUES (
                :workflow_run_id, :dataclass, :business_dt,
                :status, :started_at, :completed_at
            )
            ''',
            {
                'workflow_run_id': run.workflow_run_id,
                'dataclass': run.dataclass,
                'business_dt': run.business_dt,
                'status': run.status,
                'started_at': run.started_at,
                'completed_at': run.completed_at,
            },
        )


    def get_workflow_run(self, workflow_run_id: UUID) -> WorkflowRun:
        row = self._executor.fetch_one(
            '''
            SELECT
                workflow_run_id, dataclass, business_dt,
                status, started_at, completed_at
            FROM core.workflow_run
            WHERE workflow_run_id = :workflow_run_id
            ''',
            {'workflow_run_id': workflow_run_id},
        )

        if row is None:
            raise KeyError(f'Unknown workflow_run_id: {workflow_run_id!r}')

        return WorkflowRun(
            workflow_run_id=row['workflow_run_id'],
            dataclass=row['dataclass'],
            business_dt=row['business_dt'],
            status=RunStatus(row['status']),
            started_at=row['started_at'],
            completed_at=row['completed_at'],
        )


    def create_execution_run(self, run: ExecutionRun) -> None:
        self._executor.execute(
            '''
            INSERT INTO core.execution_run (
                run_id, workflow_run_id, parent_run_id, component,
                operation, status, started_at, completed_at,
                retry_of_run_id
            ) VALUES (
                :run_id, :workflow_run_id, :parent_run_id, :component,
                :operation, :status, :started_at, :completed_at,
                :retry_of_run_id
            )
            ''',
            {
                'run_id': run.run_id,
                'workflow_run_id': run.workflow_run_id,
                'parent_run_id': run.parent_run_id,
                'component': run.component,
                'operation': run.operation,
                'status': run.status,
                'started_at': run.started_at,
                'completed_at': run.completed_at,
                'retry_of_run_id': run.retry_of_run_id,
            },
        )


    def get_execution_run(self, run_id: UUID) -> ExecutionRun:
        row = self._executor.fetch_one(
            '''
            SELECT
                run_id, workflow_run_id, parent_run_id, component,
                operation, status, started_at, completed_at,
                retry_of_run_id
            FROM core.execution_run
            WHERE run_id = :run_id
            ''',
            {'run_id': run_id},
        )

        if row is None:
            raise KeyError(f'Unknown run_id: {run_id!r}')

        return ExecutionRun(
            run_id=row['run_id'],
            workflow_run_id=row['workflow_run_id'],
            parent_run_id=row['parent_run_id'],
            component=row['component'],
            operation=row['operation'],
            status=RunStatus(row['status']),
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            retry_of_run_id=row['retry_of_run_id'],
        )


    def get_execution_runs(
        self,
        workflow_run_id: UUID,
    ) -> tuple[ExecutionRun, ...]:
        rows = self._executor.fetch_all(
            '''
            SELECT
                run_id, workflow_run_id, parent_run_id, component,
                operation, status, started_at, completed_at,
                retry_of_run_id
            FROM core.execution_run
            WHERE workflow_run_id = :workflow_run_id
            ORDER BY started_at, run_id
            ''',
            {'workflow_run_id': workflow_run_id},
        )

        return tuple(
            ExecutionRun(
                run_id=row['run_id'],
                workflow_run_id=row['workflow_run_id'],
                parent_run_id=row['parent_run_id'],
                component=row['component'],
                operation=row['operation'],
                status=RunStatus(row['status']),
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                retry_of_run_id=row['retry_of_run_id'],
            )
            for row in rows
        )


    def update_workflow_status(
        self,
        workflow_run_id: UUID,
        status: RunStatus,
        completed_at: datetime | None = None,
    ) -> None:
        self._executor.execute(
            '''
            UPDATE core.workflow_run
            SET status = :status, completed_at = :completed_at
            WHERE workflow_run_id = :workflow_run_id
            ''',
            {
                'workflow_run_id': workflow_run_id,
                'status': status,
                'completed_at': completed_at,
            },
        )


    def update_execution_status(
        self,
        run_id: UUID,
        status: RunStatus,
        completed_at: datetime | None = None,
    ) -> None:
        self._executor.execute(
            '''
            UPDATE core.execution_run
            SET status = :status, completed_at = :completed_at
            WHERE run_id = :run_id
            ''',
            {
                'run_id': run_id,
                'status': status,
                'completed_at': completed_at,
            },
        )


    def get_workflow_summary(
        self,
        workflow_run_id: UUID,
    ) -> WorkflowRunSummary:
        workflow = self.get_workflow_run(workflow_run_id)
        executions = self.get_execution_runs(workflow_run_id)
        dependencies = self.get_workflow_dependencies(workflow_run_id)

        return WorkflowRunSummary(
            workflow=workflow,
            executions=executions,
            dependencies=dependencies,
        )


    def create_dependency(self, dependency: RunDependency) -> None:
        self._executor.execute(
            '''
            INSERT INTO core.run_dependency (
                consumer_run_id, producer_run_id, input_role
            ) VALUES (
                :consumer_run_id, :producer_run_id, :input_role
            )
            ''',
            {
                'consumer_run_id': dependency.consumer_run_id,
                'producer_run_id': dependency.producer_run_id,
                'input_role': dependency.input_role,
            },
        )


    def get_dependencies(
        self,
        consumer_run_id: UUID,
    ) -> tuple[RunDependency, ...]:
        rows = self._executor.fetch_all(
            '''
            SELECT consumer_run_id, producer_run_id, input_role
            FROM core.run_dependency
            WHERE consumer_run_id = :consumer_run_id
            ''',
            {'consumer_run_id': consumer_run_id},
        )

        return tuple(
            RunDependency(
                consumer_run_id=row['consumer_run_id'],
                producer_run_id=row['producer_run_id'],
                input_role=row['input_role'],
            )
            for row in rows
        )


    def get_workflow_dependencies(
        self,
        workflow_run_id: UUID,
    ) -> tuple[RunDependency, ...]:
        rows = self._executor.fetch_all(
            '''
            SELECT
                run_dependency.consumer_run_id,
                run_dependency.producer_run_id,
                run_dependency.input_role
            FROM core.run_dependency
            JOIN core.execution_run
                ON execution_run.run_id = run_dependency.consumer_run_id
            WHERE execution_run.workflow_run_id = :workflow_run_id
            ORDER BY
                run_dependency.consumer_run_id,
                run_dependency.producer_run_id
            ''',
            {'workflow_run_id': workflow_run_id},
        )

        return tuple(
            RunDependency(
                consumer_run_id=row['consumer_run_id'],
                producer_run_id=row['producer_run_id'],
                input_role=row['input_role'],
            )
            for row in rows
        )
