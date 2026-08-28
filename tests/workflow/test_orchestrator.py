from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from core.runs import (
    ExecutionRun,
    RunDependency,
    RunIdentity,
    RunRepository,
    RunStatus,
    RunTracker,
    WorkflowRun,
    ZoneResult,
)
from foundry.models import PipelineConfig
from gl import GLImportResult
from workflow import WorkflowOrchestrator, WorkflowResult


BUSINESS_DT = date(2026, 8, 24)

ZONES = ('staging', 'enrichment', 'reporting', 'posting', 'interface')


class _FakeRunRepository(RunRepository):
    """An in-memory stand-in for RunRepository, so RunTracker (the real,
    unmocked collaborator) can be exercised against the orchestrator
    without a database."""

    def __init__(self):
        self.workflows: dict[UUID, WorkflowRun] = {}
        self.executions: dict[UUID, ExecutionRun] = {}
        self.dependencies: list[RunDependency] = []


    def create_workflow_run(self, run):
        self.workflows[run.workflow_run_id] = run


    def get_workflow_run(self, workflow_run_id):
        if workflow_run_id not in self.workflows:
            raise KeyError(f'Unknown workflow_run_id: {workflow_run_id!r}')
        return self.workflows[workflow_run_id]


    def create_execution_run(self, run):
        self.executions[run.run_id] = run


    def get_execution_run(self, run_id):
        return self.executions[run_id]


    def get_execution_runs(self, workflow_run_id):
        return tuple(
            execution
            for execution in self.executions.values()
            if execution.workflow_run_id == workflow_run_id
        )


    def update_workflow_status(self, workflow_run_id, status, completed_at=None):
        run = self.workflows[workflow_run_id]
        self.workflows[workflow_run_id] = WorkflowRun(
            workflow_run_id=run.workflow_run_id,
            dataclass=run.dataclass,
            business_dt=run.business_dt,
            status=status,
            started_at=run.started_at,
            completed_at=completed_at,
        )


    def update_execution_status(self, run_id, status, completed_at=None):
        run = self.executions[run_id]
        self.executions[run_id] = ExecutionRun(
            run_id=run.run_id,
            workflow_run_id=run.workflow_run_id,
            parent_run_id=run.parent_run_id,
            component=run.component,
            operation=run.operation,
            status=status,
            started_at=run.started_at,
            completed_at=completed_at,
            retry_of_run_id=run.retry_of_run_id,
        )


    def create_dependency(self, dependency):
        self.dependencies.append(dependency)


def _make_run_tracker():
    return RunTracker(_FakeRunRepository())


class _FakePipeline:
    """A stand-in for BasePipeline: implements the zone(identity) API and
    rollback_execution(operation, identity), with no Spark/DataFrame
    involvement at all."""

    def __init__(self, business_dt=BUSINESS_DT, raise_in=None):
        self.config = PipelineConfig(
            dataclass='TRIAL_BALANCE',
            business_dt=business_dt,
        )
        self._raise_in = raise_in
        self.rollback_calls: list[tuple[str, RunIdentity]] = []
        self.zone_calls: dict[str, RunIdentity] = {}


    def _zone(self, name, identity):
        self.zone_calls[name] = identity
        if self._raise_in == name:
            raise ValueError(f'{name} boom')
        return ZoneResult(
            identity=identity,
            zone=name.upper(),
            status=RunStatus.SUCCEEDED,
            record_count=1,
        )


    def staging(self, identity):
        return self._zone('staging', identity)

    def enrichment(self, identity):
        return self._zone('enrichment', identity)

    def reporting(self, identity):
        return self._zone('reporting', identity)

    def posting(self, identity):
        return self._zone('posting', identity)

    def interface(self, identity):
        return self._zone('interface', identity)


    def rollback_execution(self, operation, identity):
        self.rollback_calls.append((operation, identity))


class _FakeGL:
    def __init__(self, raise_error=False, rejected_count=0):
        self._raise_error = raise_error
        self._rejected_count = rejected_count
        self.import_calls: list[tuple[RunIdentity, UUID]] = []
        self.rollback_calls: list[RunIdentity] = []


    def import_instructions(self, identity, source_producer_run_id):
        self.import_calls.append((identity, source_producer_run_id))

        if self._raise_error:
            raise ValueError('gl import boom')

        received = self._rejected_count + 1
        return GLImportResult(
            workflow_run_id=identity.workflow_run_id,
            producer_run_id=identity.run_id,
            source_producer_run_id=source_producer_run_id,
            received_count=received,
            posted_count=received - self._rejected_count,
            rejected_count=self._rejected_count,
            results=(),
        )


    def rollback_execution(self, identity):
        self.rollback_calls.append(identity)


def _executions_by_operation(repository: _FakeRunRepository, workflow_run_id: UUID):
    return {
        execution.operation: execution
        for execution in repository.get_execution_runs(workflow_run_id)
    }


# -- run_foundry: topology -----------------------------------------------

def test_run_foundry_creates_pipeline_and_all_five_zone_executions_under_one_workflow():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    result = orchestrator.run_foundry()

    repository = run_tracker._repository
    executions = _executions_by_operation(repository, result.identity.workflow_run_id)

    assert set(executions) == {'PIPELINE', 'STAGING', 'ENRICHMENT', 'REPORTING', 'POSTING', 'INTERFACE'}
    assert all(e.component == 'FOUNDRY' for e in executions.values())

    pipeline_execution = executions['PIPELINE']
    assert pipeline_execution.parent_run_id is None

    for operation in ('STAGING', 'ENRICHMENT', 'REPORTING', 'POSTING', 'INTERFACE'):
        assert executions[operation].parent_run_id == pipeline_execution.run_id


def test_run_foundry_creates_all_five_zone_to_zone_dependencies():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    result = orchestrator.run_foundry()

    repository = run_tracker._repository
    executions = _executions_by_operation(repository, result.identity.workflow_run_id)

    dependency_pairs = {
        (dep.consumer_run_id, dep.producer_run_id, dep.input_role)
        for dep in repository.dependencies
    }

    # Reporting genuinely reads both Staging and Enrichment output (see
    # TrialBalancePipeline.pre_reporting), so it depends on both.
    assert dependency_pairs == {
        (executions['ENRICHMENT'].run_id, executions['STAGING'].run_id, 'STAGING'),
        (executions['REPORTING'].run_id, executions['STAGING'].run_id, 'STAGING'),
        (executions['REPORTING'].run_id, executions['ENRICHMENT'].run_id, 'ENRICHMENT'),
        (executions['POSTING'].run_id, executions['REPORTING'].run_id, 'REPORTING'),
        (executions['INTERFACE'].run_id, executions['POSTING'].run_id, 'POSTING'),
    }


def test_run_foundry_returns_pipeline_result_with_zones_in_order():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    result = orchestrator.run_foundry()

    assert [z.zone for z in result.zones] == [
        'STAGING', 'ENRICHMENT', 'REPORTING', 'POSTING', 'INTERFACE',
    ]
    assert result.status == RunStatus.SUCCEEDED


# -- run_foundry: lifecycle ------------------------------------------------

def test_run_foundry_completes_workflow_and_pipeline_execution_on_success():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    result = orchestrator.run_foundry()

    repository = run_tracker._repository
    workflow = repository.get_workflow_run(result.identity.workflow_run_id)
    assert workflow.status == RunStatus.SUCCEEDED

    executions = _executions_by_operation(repository, result.identity.workflow_run_id)
    assert all(e.status == RunStatus.SUCCEEDED for e in executions.values())


@pytest.mark.parametrize('failing_zone', ZONES)
def test_run_foundry_rolls_back_and_fails_execution_chain_on_zone_failure(failing_zone):
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline(raise_in=failing_zone)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    with pytest.raises(ValueError, match=f'{failing_zone} boom'):
        orchestrator.run_foundry()

    repository = run_tracker._repository
    [workflow] = repository.workflows.values()
    assert workflow.status == RunStatus.FAILED

    executions = _executions_by_operation(repository, workflow.workflow_run_id)
    assert executions['PIPELINE'].status == RunStatus.FAILED
    assert executions[failing_zone.upper()].status == RunStatus.FAILED

    # Rollback ran for the failed zone, using its own identity, before the
    # execution was marked failed.
    [(operation, identity)] = pipeline.rollback_calls
    assert operation == failing_zone.upper()
    assert identity.run_id == executions[failing_zone.upper()].run_id

    # Zones preceding the failure succeeded and were not rolled back.
    preceding = ZONES[:ZONES.index(failing_zone)]
    for zone in preceding:
        assert executions[zone.upper()].status == RunStatus.SUCCEEDED


def test_run_foundry_passes_the_zones_own_identity_into_each_zone_call():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    result = orchestrator.run_foundry()

    repository = run_tracker._repository
    executions = _executions_by_operation(repository, result.identity.workflow_run_id)

    for zone in ZONES:
        identity = pipeline.zone_calls[zone]
        execution = executions[zone.upper()]
        assert identity.run_id == execution.run_id
        assert identity.workflow_run_id == execution.workflow_run_id
        assert identity.parent_run_id == execution.parent_run_id


# -- run_gl -----------------------------------------------------------------

def test_run_gl_requires_an_existing_workflow():
    run_tracker = _make_run_tracker()
    orchestrator = WorkflowOrchestrator(run_tracker, _FakePipeline(), gl=_FakeGL())

    with pytest.raises(KeyError):
        orchestrator.run_gl(uuid4())


def test_run_gl_resolves_the_workflows_foundry_interface_execution():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    repository = run_tracker._repository
    interface_execution = _executions_by_operation(repository, workflow_run_id)['INTERFACE']

    orchestrator.run_gl(workflow_run_id)

    [(identity, source_producer_run_id)] = gl.import_calls
    assert source_producer_run_id == interface_execution.run_id
    assert identity.workflow_run_id == workflow_run_id


def test_run_gl_creates_gl_import_execution_under_the_same_workflow_with_dependency():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    orchestrator.run_gl(workflow_run_id)

    repository = run_tracker._repository
    executions = _executions_by_operation(repository, workflow_run_id)
    interface_execution = executions['INTERFACE']
    gl_execution = executions['IMPORT']

    assert gl_execution.component == 'GL'
    assert gl_execution.workflow_run_id == workflow_run_id
    assert gl_execution.status == RunStatus.SUCCEEDED

    assert any(
        dep.consumer_run_id == gl_execution.run_id
        and dep.producer_run_id == interface_execution.run_id
        and dep.input_role == 'INTERFACE'
        for dep in repository.dependencies
    )


def test_run_gl_raises_when_no_successful_interface_execution_exists():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline(raise_in='interface')
    gl = _FakeGL()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    with pytest.raises(ValueError, match='boom'):
        orchestrator.run_foundry()

    [workflow_run_id] = list(run_tracker._repository.workflows)

    with pytest.raises(ValueError, match='No successful FOUNDRY/INTERFACE execution'):
        orchestrator.run_gl(workflow_run_id)


def test_run_gl_business_rejections_still_succeed_the_import_execution():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL(rejected_count=3)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    result = orchestrator.run_gl(workflow_run_id)

    assert result.rejected_count == 3

    repository = run_tracker._repository
    gl_execution = _executions_by_operation(repository, workflow_run_id)['IMPORT']
    assert gl_execution.status == RunStatus.SUCCEEDED


def test_run_gl_rolls_back_and_fails_on_technical_failure():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL(raise_error=True)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    with pytest.raises(ValueError, match='gl import boom'):
        orchestrator.run_gl(workflow_run_id)

    repository = run_tracker._repository
    gl_execution = _executions_by_operation(repository, workflow_run_id)['IMPORT']
    assert gl_execution.status == RunStatus.FAILED

    [identity] = gl.rollback_calls
    assert identity.run_id == gl_execution.run_id

    workflow = repository.get_workflow_run(workflow_run_id)
    assert workflow.status == RunStatus.FAILED


def test_run_gl_continuing_an_already_succeeded_workflow_keeps_it_succeeded():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    repository = run_tracker._repository
    assert repository.get_workflow_run(workflow_run_id).status == RunStatus.SUCCEEDED

    orchestrator.run_gl(workflow_run_id)

    assert repository.get_workflow_run(workflow_run_id).status == RunStatus.SUCCEEDED


# -- logging --------------------------------------------------------------

def test_run_foundry_zone_success_logs_operation_run_id_and_record_count(caplog):
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    with caplog.at_level('INFO', logger='workflow.orchestrator'):
        result = orchestrator.run_foundry()

    repository = run_tracker._repository
    executions = _executions_by_operation(repository, result.identity.workflow_run_id)
    staging_run_id = executions['STAGING'].run_id

    zone_success_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'Foundry zone succeeded' in r.message
    ]
    assert any(
        'STAGING' in r.message
        and str(staging_run_id) in r.message
        and 'records=1' in r.message
        for r in zone_success_records
    )


def test_run_gl_success_logs_received_posted_and_rejected_counts(caplog):
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL(rejected_count=2)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    with caplog.at_level('INFO', logger='workflow.orchestrator'):
        result = orchestrator.run_gl(workflow_run_id)

    success_records = [
        r for r in caplog.records
        if r.levelname == 'INFO' and 'GL import succeeded' in r.message
    ]
    assert len(success_records) == 1
    message = success_records[0].message
    assert f'received={result.received_count}' in message
    assert f'posted={result.posted_count}' in message
    assert f'rejected={result.rejected_count}' in message


@pytest.mark.parametrize('failing_zone', ZONES)
def test_run_foundry_failure_logs_rollback_warning_and_one_exception(caplog, failing_zone):
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline(raise_in=failing_zone)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    with caplog.at_level('INFO', logger='workflow.orchestrator'):
        with pytest.raises(ValueError, match=f'{failing_zone} boom'):
            orchestrator.run_foundry()

    warning_records = [
        r for r in caplog.records
        if r.levelname == 'WARNING' and 'Foundry zone rollback initiated' in r.message
    ]
    assert len(warning_records) == 1
    assert failing_zone.upper() in warning_records[0].message

    exception_records = [
        r for r in caplog.records
        if r.levelname == 'ERROR' and 'Foundry zone failed' in r.message and r.exc_info
    ]
    assert len(exception_records) == 1
    assert failing_zone.upper() in exception_records[0].message


def test_run_gl_failure_logs_rollback_warning_and_one_exception(caplog):
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL(raise_error=True)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    with caplog.at_level('INFO', logger='workflow.orchestrator'):
        with pytest.raises(ValueError, match='gl import boom'):
            orchestrator.run_gl(workflow_run_id)

    warning_records = [
        r for r in caplog.records
        if r.levelname == 'WARNING' and 'GL rollback initiated' in r.message
    ]
    assert len(warning_records) == 1

    exception_records = [
        r for r in caplog.records
        if r.levelname == 'ERROR' and 'GL import failed' in r.message and r.exc_info
    ]
    assert len(exception_records) == 1


# -- run_workflow -------------------------------------------------------

def test_run_workflow_creates_exactly_one_workflow_with_foundry_and_gl():
    run_tracker = _make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    result = orchestrator.run_workflow()

    assert isinstance(result, WorkflowResult)

    repository = run_tracker._repository
    assert len(repository.workflows) == 1

    workflow_run_id = result.foundry.identity.workflow_run_id
    assert result.gl.workflow_run_id == workflow_run_id

    executions = _executions_by_operation(repository, workflow_run_id)
    assert set(executions) == {
        'PIPELINE', 'STAGING', 'ENRICHMENT', 'REPORTING', 'POSTING', 'INTERFACE', 'IMPORT',
    }

    workflow = repository.get_workflow_run(workflow_run_id)
    assert workflow.status == RunStatus.SUCCEEDED
