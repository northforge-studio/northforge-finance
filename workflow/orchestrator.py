from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from core.logging import get_logger
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


logger = get_logger(__name__)


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
        except Exception as exc:
            self._fail_workflow(workflow.workflow_run_id, exc)
            raise

        self._complete_workflow(workflow.workflow_run_id)

        return result


    def run_gl(self, workflow_run_id: UUID) -> GLImportResult:
        # Continuing an existing business workflow: GL must never create
        # a new one, and never guess which Interface batch to read.
        workflow = self._run_tracker.get_workflow_run(workflow_run_id)

        try:
            result = self._execute_gl(workflow)
        except Exception as exc:
            self._fail_workflow(workflow.workflow_run_id, exc)
            raise

        # The workflow may already be SUCCEEDED from a prior run_foundry()
        # call; re-affirming completion here (rather than adding a new
        # RunStatus) is the minimal way to let GL continue it.
        self._complete_workflow(workflow.workflow_run_id)

        return result


    def run_workflow(self) -> WorkflowResult:
        workflow = self._start_workflow()

        try:
            foundry_result = self._execute_foundry(workflow.workflow_run_id)
            gl_result = self._execute_gl(workflow)
        except Exception as exc:
            self._fail_workflow(workflow.workflow_run_id, exc)
            raise

        self._complete_workflow(workflow.workflow_run_id)

        return WorkflowResult(foundry=foundry_result, gl=gl_result)


    def _complete_workflow(self, workflow_run_id: UUID) -> None:
        self._run_tracker.complete_workflow(workflow_run_id)
        logger.info('Workflow succeeded | workflow_run_id=%s', workflow_run_id)


    def _fail_workflow(self, workflow_run_id: UUID, exc: Exception) -> None:
        self._run_tracker.fail_workflow(workflow_run_id)
        # The layer that owns the failure (zone/GL) already logged the
        # traceback via logger.exception; this is a concise status line only.
        logger.error(
            'Workflow failed | workflow_run_id=%s | error=%s',
            workflow_run_id, exc,
        )


    def _start_workflow(self) -> WorkflowRun:
        config = self._foundry_pipeline.config

        workflow = self._run_tracker.start_workflow(
            dataclass=config.dataclass,
            business_dt=config.business_dt,
        )

        logger.info(
            'Workflow started | workflow_run_id=%s | dataclass=%s | business_dt=%s',
            workflow.workflow_run_id, workflow.dataclass, workflow.business_dt,
        )

        return workflow


    def _execute_foundry(self, workflow_run_id: UUID) -> PipelineResult:
        pipeline_execution = self._run_tracker.start_execution(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation='PIPELINE',
        )

        logger.info(
            'Foundry pipeline started | run_id=%s | workflow_run_id=%s',
            pipeline_execution.run_id, workflow_run_id,
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
                zone=lambda identity: self._foundry_pipeline.enrichment(
                    identity,
                    source_producer_run_id=staging_result.identity.run_id,
                ),
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
                depends_on=((staging_result, 'STAGING'),),
            )
            reporting_result = self._run_foundry_zone(
                operation='REPORTING',
                zone=lambda identity: self._foundry_pipeline.reporting(
                    identity,
                    staging_producer_run_id=staging_result.identity.run_id,
                    enrichment_producer_run_id=enrichment_result.identity.run_id,
                ),
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
                depends_on=(
                    (staging_result, 'STAGING'),
                    (enrichment_result, 'ENRICHMENT'),
                ),
            )
            posting_result = self._run_foundry_zone(
                operation='POSTING',
                zone=lambda identity: self._foundry_pipeline.posting(
                    identity,
                    source_producer_run_id=reporting_result.identity.run_id,
                ),
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
                depends_on=((reporting_result, 'REPORTING'),),
            )
            interface_result = self._run_foundry_zone(
                operation='INTERFACE',
                zone=lambda identity: self._foundry_pipeline.interface(
                    identity,
                    source_producer_run_id=posting_result.identity.run_id,
                ),
                workflow_run_id=workflow_run_id,
                parent_run_id=pipeline_execution.run_id,
                depends_on=((posting_result, 'POSTING'),),
            )
        except Exception:
            self._run_tracker.fail_execution(pipeline_execution.run_id)
            raise

        self._run_tracker.complete_execution(pipeline_execution.run_id)

        total_records = sum(
            zone.record_count
            for zone in (
                staging_result, enrichment_result, reporting_result,
                posting_result, interface_result,
            )
        )
        logger.info(
            'Foundry pipeline succeeded | run_id=%s | workflow_run_id=%s | records=%d',
            pipeline_execution.run_id, workflow_run_id, total_records,
        )

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
        depends_on: tuple[tuple[ZoneResult, str], ...] = (),
    ) -> ZoneResult:
        execution = self._run_tracker.start_execution(
            workflow_run_id=workflow_run_id,
            component='FOUNDRY',
            operation=operation,
            parent_run_id=parent_run_id,
        )

        for producer_result, input_role in depends_on:
            self._run_tracker.add_dependency(
                consumer_run_id=execution.run_id,
                producer_run_id=producer_result.identity.run_id,
                input_role=input_role,
            )

        identity = RunIdentity(
            workflow_run_id=workflow_run_id,
            run_id=execution.run_id,
            parent_run_id=parent_run_id,
        )

        logger.info(
            'Foundry zone started | operation=%s | run_id=%s | workflow_run_id=%s',
            operation, execution.run_id, workflow_run_id,
        )

        try:
            result = zone(identity)
        except Exception:
            logger.warning(
                'Foundry zone rollback initiated | component=FOUNDRY | operation=%s | run_id=%s',
                operation, execution.run_id,
            )
            self._foundry_pipeline.rollback_execution(operation, identity)
            self._run_tracker.fail_execution(execution.run_id)
            logger.exception(
                'Foundry zone failed | operation=%s | run_id=%s | workflow_run_id=%s',
                operation, execution.run_id, workflow_run_id,
            )
            raise

        self._run_tracker.complete_execution(execution.run_id)

        logger.info(
            'Foundry zone succeeded | operation=%s | run_id=%s | workflow_run_id=%s | records=%d',
            operation, execution.run_id, workflow_run_id, result.record_count,
        )

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

        logger.info(
            'GL import started | run_id=%s | workflow_run_id=%s | source_producer_run_id=%s',
            gl_execution.run_id, workflow.workflow_run_id, interface_execution.run_id,
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
            logger.warning(
                'GL rollback initiated | component=GL | operation=IMPORT | run_id=%s',
                gl_execution.run_id,
            )
            self._gl.rollback_execution(identity)
            self._run_tracker.fail_execution(gl_execution.run_id)
            logger.exception(
                'GL import failed | run_id=%s | workflow_run_id=%s',
                gl_execution.run_id, workflow.workflow_run_id,
            )
            raise

        self._run_tracker.complete_execution(gl_execution.run_id)

        logger.info(
            'GL import succeeded | run_id=%s | workflow_run_id=%s | '
            'received=%d | posted=%d | rejected=%d | source_producer_run_id=%s',
            gl_execution.run_id, workflow.workflow_run_id,
            result.received_count, result.posted_count, result.rejected_count,
            interface_execution.run_id,
        )

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
