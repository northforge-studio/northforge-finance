from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from core.runs.models import (
    RunStatus,
    ZoneResult,
)
from foundry.models import PipelineConfig
from gl.models import GLImportResult
from tests.support.constants import BUSINESS_DT
from tests.support.fakes import make_run_tracker
from tests.support.pipelines import NoOpPipeline
from workflow import WorkflowOrchestrator

ZONES = ('staging', 'enrichment', 'reporting', 'posting', 'interface')


# -- fakes -----------------------------------------------------------------


class _FakePipeline(NoOpPipeline):
    """A NoOpPipeline whose zone(identity) methods succeed, or raise in the
    zone named by raise_in, with no Spark/DataFrame involvement at all."""

    def __init__(self, raise_in=None):
        super().__init__(
            config=PipelineConfig(dataclass='TRIAL_BALANCE', business_dt=BUSINESS_DT),
            atlas=MagicMock(),
            reference=MagicMock(),
            spec=MagicMock(),
        )
        self._raise_in = raise_in

    def _zone(self, name, identity):
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


class _FakeGL:
    """Implements GLClientProtocol; import_instructions optionally fails and
    rollback_execution is a no-op. Every other method is unsupported."""

    def __init__(self, raise_error=False, rejected_count=0):
        self._raise_error = raise_error
        self._rejected_count = rejected_count

    def import_instructions(self, identity, source_producer_run_id):
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

    def rollback_execution(self, identity): ...

    def get_segment_default(self, segment_type, *, entity_cd=None):
        raise NotImplementedError('_FakeGL.get_segment_default')

    def get_segment_defaults(self):
        raise NotImplementedError('_FakeGL.get_segment_defaults')

    def resolve_segment(
        self, segment_type, segment_value, *, business_dt, entity_cd=None
    ):
        raise NotImplementedError('_FakeGL.resolve_segment')

    def resolve_segments(self, segments, *, business_dt):
        raise NotImplementedError('_FakeGL.resolve_segments')

    def validate_instruction(self, instruction):
        raise NotImplementedError('_FakeGL.validate_instruction')

    def process_instruction(self, instruction):
        raise NotImplementedError('_FakeGL.process_instruction')

    def get_postings(self, workflow_run_id):
        raise NotImplementedError('_FakeGL.get_postings')

    def get_rejections(self, workflow_run_id):
        raise NotImplementedError('_FakeGL.get_rejections')


# -- run_foundry: topology -------------------------------------------------


def test_run_foundry_returns_pipeline_result_with_zones_in_order():
    run_tracker = make_run_tracker()
    pipeline = _FakePipeline()
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    result = orchestrator.run_foundry()

    assert [z.zone for z in result.zones] == [
        'STAGING',
        'ENRICHMENT',
        'REPORTING',
        'POSTING',
        'INTERFACE',
    ]
    assert result.status == RunStatus.SUCCEEDED


# -- run_gl ----------------------------------------------------------------


def test_run_gl_requires_an_existing_workflow():
    run_tracker = make_run_tracker()
    orchestrator = WorkflowOrchestrator(run_tracker, _FakePipeline(), gl=_FakeGL())

    with pytest.raises(KeyError, match='Unknown workflow_run_id'):
        orchestrator.run_gl(uuid4())


# -- logging ---------------------------------------------------------------


def test_run_gl_success_logs_received_posted_and_rejected_counts(caplog):
    run_tracker = make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL(rejected_count=2)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    with caplog.at_level('INFO', logger='workflow.orchestrator'):
        result = orchestrator.run_gl(workflow_run_id)

    success_records = [
        r
        for r in caplog.records
        if r.levelname == 'INFO' and 'GL import succeeded' in r.message
    ]
    assert len(success_records) == 1
    message = success_records[0].message
    assert f'received={result.received_count}' in message
    assert f'posted={result.posted_count}' in message
    assert f'rejected={result.rejected_count}' in message


@pytest.mark.parametrize('failing_zone', ZONES)
def test_run_foundry_failure_logs_rollback_warning_and_one_exception(
    caplog, failing_zone
):
    run_tracker = make_run_tracker()
    pipeline = _FakePipeline(raise_in=failing_zone)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=_FakeGL())

    with caplog.at_level('INFO', logger='workflow.orchestrator'):
        with pytest.raises(ValueError, match=f'{failing_zone} boom'):
            orchestrator.run_foundry()

    warning_records = [
        r
        for r in caplog.records
        if r.levelname == 'WARNING' and 'Foundry zone rollback initiated' in r.message
    ]
    assert len(warning_records) == 1
    assert failing_zone.upper() in warning_records[0].message

    exception_records = [
        r
        for r in caplog.records
        if r.levelname == 'ERROR' and 'Foundry zone failed' in r.message and r.exc_info
    ]
    assert len(exception_records) == 1
    assert failing_zone.upper() in exception_records[0].message


def test_run_gl_failure_logs_rollback_warning_and_one_exception(caplog):
    run_tracker = make_run_tracker()
    pipeline = _FakePipeline()
    gl = _FakeGL(raise_error=True)
    orchestrator = WorkflowOrchestrator(run_tracker, pipeline, gl=gl)

    foundry_result = orchestrator.run_foundry()
    workflow_run_id = foundry_result.identity.workflow_run_id

    with caplog.at_level('INFO', logger='workflow.orchestrator'):
        with pytest.raises(ValueError, match='gl import boom'):
            orchestrator.run_gl(workflow_run_id)

    warning_records = [
        r
        for r in caplog.records
        if r.levelname == 'WARNING' and 'GL rollback initiated' in r.message
    ]
    assert len(warning_records) == 1

    exception_records = [
        r
        for r in caplog.records
        if r.levelname == 'ERROR' and 'GL import failed' in r.message and r.exc_info
    ]
    assert len(exception_records) == 1
