from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from core.runs import (
    ExecutionRun,
    PipelineResult,
    RunIdentity,
    RunStatus,
    RunTracker,
    WorkflowRun,
    ZoneResult,
)
from foundry.pipeline import BasePipeline
from gl import GLClient, GLImportResult


@dataclass(frozen=True)
class WorkflowResult:
    foundry: PipelineResult
    gl: GLImportResult


class WorkflowOrchestrator:
    """Owns execution/workflow lifecycle across Foundry and GL.

    Foundry and GL each own their own domain processing and rollback
    mechanics; this class decides when to start/complete/fail executions,
    how the execution topology and RunDependency lineage are shaped, and
    when a failed execution's domain rollback should run.
    """

    def __init__(
        self,
        run_tracker: RunTracker,
        foundry_pipeline: BasePipeline,
        gl: GLClient,
    ):
        self._run_tracker = run_tracker
        self._foundry_pipeline = foundry_pipeline
        self._gl = gl


    def run_foundry(self) -> PipelineResult:
        workflow = self._start_workflow()

        try:
            result = self._execute_foundry(workflow.workflow_run_id)
        except Exception:
            self._run_tracker.fail_workflow(workflow.workflow_run_id)
            raise

        self._run_tracker.complete_workflow(workflow.workflow_run_id)

        return result


    def run_gl(self, workflow_run_id: UUID) -> GLImportResult:
        # Continuing an existing business workflow: GL must never create
        # a new one, and never guess which Interface batch to read.
        workflow = self._run_tracker.get_workflow_run(workflow_run_id)

        try:
            result = self._execute_gl(workflow)
        except Exception:
            self._run_tracker.fail_workflow(workflow.workflow_run_id)
            raise

        # The workflow may already be SUCCEEDED from a prior run_foundry()
        # call; re-affirming completion here (rather than adding a new
        # RunStatus) is the minimal way to let GL continue it.
        self._run_tracker.complete_workflow(workflow.workflow_run_id)

        return result


    def run_workflow(self) -> WorkflowResult:
        workflow = self._start_workflow()

        try:
            foundry_result = self._execute_foundry(workflow.workflow_run_id)
            gl_result = self._execute_gl(workflow)
        except Exception:
            self._run_tracker.fail_workflow(workflow.workflow_run_id)
            raise

        self._run_tracker.complete_workflow(workflow.workflow_run_id)

        return WorkflowResult(foundry=foundry_result, gl=gl_result)


    def _start_workflow(self) -> WorkflowRun:
        config = self._foundry_pipeline.config

        return self._run_tracker.start_workflow(
            dataclass=config.dataclass,
            business_dt=config.business_dt,
            batch_id=config.batch_id,
        )


    def _execute_foundry(self, workflow_run_id: UUID) -> PipelineResult:
        pipeline_execution = self._run_tracker.start_execution(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation='PIPELINE',
        )

        try:
            staging_result = self._run_foundry_zone(
                operation='STAGING',
                zone=self._foundry_pipeline.staging,
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
            )
            enrichment_result = self._run_foundry_zone(
                operation='ENRICHMENT',
                zone=self._foundry_pipeline.enrichment,
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
                depends_on=staging_result,
                input_role='STAGING',
            )
            reporting_result = self._run_foundry_zone(
                operation='REPORTING',
                zone=self._foundry_pipeline.reporting,
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
                depends_on=enrichment_result,
                input_role='ENRICHMENT',
            )
            posting_result = self._run_foundry_zone(
                operation='POSTING',
                zone=self._foundry_pipeline.posting,
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
                depends_on=reporting_result,
                input_role='REPORTING',
            )
            interface_result = self._run_foundry_zone(
                operation='INTERFACE',
                zone=self._foundry_pipeline.interface,
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
                depends_on=posting_result,
                input_role='POSTING',
            )
        except Exception:
            self._run_tracker.fail_execution(pipeline_execution.run_id)
            raise

        self._run_tracker.complete_execution(pipeline_execution.run_id)

        return PipelineResult(
            identity=RunIdentity(
                workflow_run_id=workflow_run_id,
                run_id=pipeline_execution.run_id,
                parent_run_id=pipeline_execution.parent_run_id,
            ),
            status=RunStatus.SUCCEEDED,
            zones=(
                staging_result,
                enrichment_result,
                reporting_result,
                posting_result,
                interface_result,
            ),
        )


    def _run_foundry_zone(
        self,
        *,
        operation: str,
        zone: Callable[[RunIdentity], ZoneResult],
        workflow_run_id: UUID,
        parent_run_id: UUID,
        depends_on: ZoneResult | None = None,
        input_role: str | None = None,
    ) -> ZoneResult:
        execution = self._run_tracker.start_execution(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation=operation,
            parent_run_id=parent_run_id,
        )

        if depends_on is not None:
            self._run_tracker.add_dependency(
                consumer_run_id=execution.run_id,
                producer_run_id=depends_on.identity.run_id,
                input_role=input_role,
            )

        identity = RunIdentity(
            workflow_run_id=workflow_run_id,
            run_id=execution.run_id,
            parent_run_id=parent_run_id,
        )

        try:
            result = zone(identity)
        except Exception:
            self._foundry_pipeline.rollback_execution(operation, identity)
            self._run_tracker.fail_execution(execution.run_id)
            raise

        self._run_tracker.complete_execution(execution.run_id)

        return result


    def _execute_gl(self, workflow: WorkflowRun) -> GLImportResult:
        interface_execution = self._find_interface_execution(workflow.workflow_run_id)

        gl_execution = self._run_tracker.start_execution(
            workflow_run_id=workflow.workflow_run_id,
            component='GL',
            operation='IMPORT',
        )
        self._run_tracker.add_dependency(
            consumer_run_id=gl_execution.run_id,
            producer_run_id=interface_execution.run_id,
            input_role='INTERFACE',
        )

        identity = RunIdentity(
            workflow_run_id=workflow.workflow_run_id,
            run_id=gl_execution.run_id,
            parent_run_id=None,
        )

        try:
            # A GLImportResult with rejected_count > 0 is still a
            # successful execution: only a raised exception (a technical
            # failure) fails GL/IMPORT here.
            result = self._gl.import_instructions(
                identity=identity,
                source_producer_run_id=interface_execution.run_id,
            )
        except Exception:
            self._gl.rollback_execution(identity)
            self._run_tracker.fail_execution(gl_execution.run_id)
            raise

        self._run_tracker.complete_execution(gl_execution.run_id)

        return result


    def _find_interface_execution(self, workflow_run_id: UUID) -> ExecutionRun:
        executions = self._run_tracker.get_execution_runs(workflow_run_id)

        candidates = [
            execution
            for execution in executions
            if execution.component == 'FOUNDRY'
            and execution.operation == 'INTERFACE'
            and execution.status == RunStatus.SUCCEEDED
        ]

        if not candidates:
            raise ValueError(
                'No successful FOUNDRY/INTERFACE execution found for '
                f'workflow_run_id={workflow_run_id!r}'
            )

        return max(candidates, key=lambda execution: execution.started_at)
