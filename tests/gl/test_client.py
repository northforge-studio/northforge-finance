from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from pyspark.sql import DataFrame

from core.store import CsvStore
from core.runs.models import RunIdentity

from registry.models import GLSegmentType

from gl import GLClient
from gl.models import GLInstruction, GLSegments, GLSegmentResolution
from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA


BUSINESS_DT = date(2026, 1, 1)


class _FakeRegistryClient:
    """Duck-types RegistryClient.validate_segment for delegation tests."""

    def __init__(self, valid_segments):
        self._valid_segments = valid_segments


    def validate_segment(self, segment, business_dt, segment_cd):
        return (segment, business_dt, segment_cd) in self._valid_segments


@pytest.fixture(scope='module')
def registry():
    return _FakeRegistryClient({
        (GLSegmentType.DEPARTMENT, BUSINESS_DT, 'USGL99'),
        (GLSegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
        (GLSegmentType.ENTITY, BUSINESS_DT, 'USMKTS'),
        (GLSegmentType.BRANCH, BUSINESS_DT, '100'),
        (GLSegmentType.ACCOUNT, BUSINESS_DT, '123456'),
        (GLSegmentType.AFFILIATE, BUSINESS_DT, '999999'),
        (GLSegmentType.PRODUCT, BUSINESS_DT, 'PRD1'),
        (GLSegmentType.BOOK, BUSINESS_DT, 'BK1'),
        (GLSegmentType.SOURCE, BUSINESS_DT, 'SRC1'),
    })


@pytest.fixture(scope='module')
def gl(spark, registry):
    return GLClient.from_csv(
        spark=spark,
        segment_default_path='data/gl/segment_default.csv',
        registry=registry,
    )


def test_get_segment_default_returns_contextual_default(gl):
    assert gl.get_segment_default(GLSegmentType.DEPARTMENT, entity_cd='USMKTS') == 'USGL99'


def test_get_segment_default_falls_back_to_global(gl):
    assert gl.get_segment_default(GLSegmentType.SUB_ACCOUNT, entity_cd='USMKTS') == '990001'


def test_get_segment_default_without_entity_cd_uses_global_only(gl):
    assert gl.get_segment_default(GLSegmentType.PRODUCT) == '990003'


def test_get_segment_default_returns_none_for_non_defaultable_segments(gl):
    assert gl.get_segment_default(GLSegmentType.ENTITY, entity_cd='USMKTS') is None
    assert gl.get_segment_default(GLSegmentType.SOURCE, entity_cd='USMKTS') is None


def test_resolve_segment_delegates_to_manager_for_invalid_supplied_value(gl):
    result = gl.resolve_segment(
        GLSegmentType.DEPARTMENT, 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USMKTS',
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.DEPARTMENT,
        supplied_value='BOGUS',
        resolved_value='USGL99',
        defaulted=True,
    )


def test_resolve_segment_delegates_to_manager_for_valid_supplied_value(gl):
    result = gl.resolve_segment(
        GLSegmentType.DEPARTMENT, 'USGL99',
        business_dt=BUSINESS_DT,
        entity_cd='USMKTS',
    )

    assert result == GLSegmentResolution(
        segment_type=GLSegmentType.DEPARTMENT,
        supplied_value='USGL99',
        resolved_value='USGL99',
        defaulted=False,
    )


def _valid_segments() -> GLSegments:
    return GLSegments(
        entity_cd='USMKTS',
        dept_cd='USGL99',
        branch_cd='100',
        gl_account='123456',
        sub_account='UNASSIGNED',
        affiliate_cd='999999',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
    )


def test_resolve_segments_delegates_to_manager_when_all_supplied_valid(gl):
    result = gl.resolve_segments(_valid_segments(), business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == _valid_segments()
    assert len(result.resolutions) == 9


def test_resolve_segments_delegates_to_manager_for_invalid_defaultable_segment(gl):
    supplied = replace(_valid_segments(), dept_cd='BOGUS')

    result = gl.resolve_segments(supplied, business_dt=BUSINESS_DT)

    assert result.resolved is True
    assert result.segments == _valid_segments()

    dept_resolution = next(
        r for r in result.resolutions if r.segment_type == GLSegmentType.DEPARTMENT
    )
    assert dept_resolution.supplied_value == 'BOGUS'
    assert dept_resolution.resolved_value == 'USGL99'
    assert dept_resolution.defaulted is True


def _valid_instruction() -> GLInstruction:
    return GLInstruction(
        workflow_run_id=uuid4(),
        producer_run_id=uuid4(),
        dataclass='TRIAL_BALANCE',
        transaction_number='TXN-1',
        line_number='1',
        foundry_rule_id='RULE-1',
        posting_id='POST-1',
        posting_stream='STREAM-1',
        src_record_id='REC-1',
        src_app_cd='NFM',
        entity_cd='USMKTS',
        dept_cd='USGL99',
        branch_cd='100',
        gl_account='123456',
        sub_account='UNASSIGNED',
        affiliate_cd='999999',
        product_cd='PRD1',
        book_cd='BK1',
        source_cd='SRC1',
        cr_dr_ind='DR',
        transaction_currency='USD',
        transaction_amount=Decimal('100.00'),
        accounted_currency='USD',
        accounted_amount=Decimal('100.00'),
        fx_rate=Decimal('1.0'),
        as_of_date=date(2026, 1, 1),
        business_date=date(2026, 1, 1),
    )


def test_validate_instruction_delegates_to_manager_for_valid_instruction(gl):
    result = gl.validate_instruction(_valid_instruction())

    assert result.valid is True
    assert result.errors == ()


def test_validate_instruction_delegates_to_manager_for_invalid_instruction(gl):
    instruction = replace(_valid_instruction(), cr_dr_ind='XX')

    result = gl.validate_instruction(instruction)

    assert result.valid is False
    assert 'INVALID_CR_DR_IND' in result.errors


# -- process_instruction / import_instructions -----------------------------

@pytest.fixture
def gl_with_posting_support(spark, registry, tmp_path):
    return GLClient.from_csv(
        spark=spark,
        segment_default_path='data/gl/segment_default.csv',
        registry=registry,
        posting_path=tmp_path / 'POSTING',
        rejection_path=tmp_path / 'REJECTION',
        interface_trial_balance_path=tmp_path / 'INTERFACE_TRIAL_BALANCE',
    )


def test_process_instruction_delegates_to_manager_for_valid_instruction(
    gl_with_posting_support,
):
    result = gl_with_posting_support.process_instruction(_valid_instruction())

    assert result.posted is True
    assert result.posting is not None
    assert result.rejection is None


def test_process_instruction_delegates_to_manager_for_invalid_instruction(
    gl_with_posting_support,
):
    instruction = replace(_valid_instruction(), cr_dr_ind='XX')

    result = gl_with_posting_support.process_instruction(instruction)

    assert result.posted is False
    assert result.posting is None
    assert result.rejection.rejection_type == 'STRUCTURAL_VALIDATION'


def test_rollback_execution_delegates_to_manager(gl_with_posting_support):
    identity = RunIdentity(workflow_run_id=uuid4(), run_id=uuid4(), parent_run_id=None)

    # Should not raise even with nothing written for this run yet.
    gl_with_posting_support.rollback_execution(identity)


def test_import_instructions_delegates_to_manager(spark, tmp_path, gl_with_posting_support):
    instruction = _valid_instruction()
    row = (
        str(instruction.workflow_run_id),
        str(instruction.producer_run_id),
        instruction.dataclass,
        instruction.transaction_number,
        instruction.line_number,
        instruction.entity_cd,
        instruction.branch_cd,
        instruction.dept_cd,
        instruction.gl_account,
        instruction.sub_account,
        instruction.affiliate_cd,
        instruction.product_cd,
        instruction.book_cd,
        instruction.source_cd,
        instruction.cr_dr_ind,
        instruction.foundry_rule_id,
        instruction.posting_id,
        instruction.posting_stream,
        instruction.src_record_id,
        instruction.src_app_cd,
        instruction.transaction_currency,
        instruction.transaction_amount,
        instruction.accounted_currency,
        instruction.accounted_amount,
        instruction.fx_rate,
        instruction.as_of_date,
        instruction.business_date,
    )
    interface_store = CsvStore(
        spark=spark,
        table_locations={
            'INTERFACE_TRIAL_BALANCE': tmp_path / 'INTERFACE_TRIAL_BALANCE',
        },
    )
    df = spark.createDataFrame([row], schema=INTERFACE_TRIAL_BALANCE_SCHEMA)
    interface_store.write(df, table_name='INTERFACE_TRIAL_BALANCE')

    # GL's execution belongs to the same workflow as the Interface data it
    # is reading; only the run_id (GL's own producer identity) is new.
    identity = RunIdentity(
        workflow_run_id=instruction.workflow_run_id,
        run_id=uuid4(),
        parent_run_id=None,
    )
    result = gl_with_posting_support.import_instructions(
        identity=identity,
        source_producer_run_id=instruction.producer_run_id,
    )

    assert result.received_count == 1
    assert result.posted_count == 1
    assert result.rejected_count == 0


# -- get_postings / get_rejections --------------------------------------

def test_get_postings_returns_a_dataframe_of_only_the_named_workflows_rows(
    gl_with_posting_support,
):
    kept = _valid_instruction()
    other = replace(
        _valid_instruction(),
        transaction_number='TXN-2',
        workflow_run_id=uuid4(),
        producer_run_id=uuid4(),
    )

    posted = gl_with_posting_support.process_instruction(kept)
    gl_with_posting_support.process_instruction(other)

    result = gl_with_posting_support.get_postings(kept.workflow_run_id)

    assert isinstance(result, DataFrame)
    rows = result.collect()
    assert len(rows) == 1
    assert UUID(rows[0]['GL_POSTING_ID']) == posted.posting.gl_posting_id
    assert UUID(rows[0]['WORKFLOW_RUN_ID']) == kept.workflow_run_id
    # PRODUCER_RUN_ID remains present and unchanged as exact lineage.
    assert UUID(rows[0]['PRODUCER_RUN_ID']) == kept.producer_run_id


def test_get_rejections_returns_a_dataframe_of_only_the_named_workflows_rows(
    gl_with_posting_support,
):
    kept = replace(_valid_instruction(), cr_dr_ind='XX')
    other = replace(
        _valid_instruction(),
        transaction_number='TXN-2',
        cr_dr_ind='XX',
        workflow_run_id=uuid4(),
        producer_run_id=uuid4(),
    )

    rejected = gl_with_posting_support.process_instruction(kept)
    gl_with_posting_support.process_instruction(other)

    result = gl_with_posting_support.get_rejections(kept.workflow_run_id)

    assert isinstance(result, DataFrame)
    rows = result.collect()
    assert len(rows) == 1
    assert UUID(rows[0]['GL_REJECTION_ID']) == rejected.rejection.gl_rejection_id
    assert UUID(rows[0]['WORKFLOW_RUN_ID']) == kept.workflow_run_id
    assert UUID(rows[0]['PRODUCER_RUN_ID']) == kept.producer_run_id
