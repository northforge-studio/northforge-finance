from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from pyspark.sql import DataFrame

from core.store import CsvStore
from core.runs import RunIdentity

from registry import SegmentType

from gl import GLClient, GLInstruction, GLSegments, SegmentResolution
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
        (SegmentType.DEPARTMENT, BUSINESS_DT, '9999'),
        (SegmentType.SUB_ACCOUNT, BUSINESS_DT, 'UNASSIGNED'),
        (SegmentType.ENTITY, BUSINESS_DT, 'USM'),
        (SegmentType.BRANCH, BUSINESS_DT, '100'),
        (SegmentType.ACCOUNT, BUSINESS_DT, '123456'),
        (SegmentType.AFFILIATE, BUSINESS_DT, '999999'),
        (SegmentType.PRODUCT, BUSINESS_DT, 'PRD1'),
        (SegmentType.BOOK, BUSINESS_DT, 'BK1'),
        (SegmentType.SOURCE, BUSINESS_DT, 'SRC1'),
    })


@pytest.fixture(scope='module')
def gl(spark, registry):
    return GLClient.from_csv(
        spark=spark,
        segment_default_path='data/gl/segment_defaults.csv',
        registry=registry,
    )


def test_get_segment_default_returns_contextual_default(gl):
    assert gl.get_segment_default('DEPT_CD', entity_cd='USM') == '9999'


def test_get_segment_default_falls_back_to_global(gl):
    assert gl.get_segment_default('SUB_ACCOUNT', entity_cd='USM') == 'UNASSIGNED'


def test_get_segment_default_without_entity_cd_uses_global_only(gl):
    assert gl.get_segment_default('PRODUCT_CD') == '999999'


def test_get_segment_default_returns_none_for_non_defaultable_segments(gl):
    assert gl.get_segment_default('ENTITY_CD', entity_cd='USM') is None
    assert gl.get_segment_default('SOURCE_CD', entity_cd='USM') is None


def test_resolve_segment_delegates_to_manager_for_invalid_supplied_value(gl):
    result = gl.resolve_segment(
        'DEPT_CD', 'BOGUS',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='DEPT_CD',
        supplied_value='BOGUS',
        resolved_value='9999',
        defaulted=True,
    )


def test_resolve_segment_delegates_to_manager_for_valid_supplied_value(gl):
    result = gl.resolve_segment(
        'DEPT_CD', '9999',
        business_dt=BUSINESS_DT,
        entity_cd='USM',
    )

    assert result == SegmentResolution(
        segment_type='DEPT_CD',
        supplied_value='9999',
        resolved_value='9999',
        defaulted=False,
    )


def _valid_segments() -> GLSegments:
    return GLSegments(
        entity_cd='USM',
        dept_cd='9999',
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

    dept_resolution = next(r for r in result.resolutions if r.segment_type == 'DEPT_CD')
    assert dept_resolution.supplied_value == 'BOGUS'
    assert dept_resolution.resolved_value == '9999'
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
        entity_cd='USM',
        dept_cd='9999',
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
        segment_default_path='data/gl/segment_defaults.csv',
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
        instruction.dept_cd,
        instruction.branch_cd,
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

def test_get_postings_returns_a_dataframe_of_only_the_named_producers_rows(
    gl_with_posting_support,
):
    kept = _valid_instruction()
    other = replace(_valid_instruction(), transaction_number='TXN-2', producer_run_id=uuid4())

    posted = gl_with_posting_support.process_instruction(kept)
    gl_with_posting_support.process_instruction(other)

    result = gl_with_posting_support.get_postings(kept.producer_run_id)

    assert isinstance(result, DataFrame)
    rows = result.collect()
    assert len(rows) == 1
    assert UUID(rows[0]['GL_POSTING_ID']) == posted.posting.gl_posting_id
    assert UUID(rows[0]['PRODUCER_RUN_ID']) == kept.producer_run_id


def test_get_rejections_returns_a_dataframe_of_only_the_named_producers_rows(
    gl_with_posting_support,
):
    kept = replace(_valid_instruction(), cr_dr_ind='XX')
    other = replace(
        _valid_instruction(),
        transaction_number='TXN-2',
        cr_dr_ind='XX',
        producer_run_id=uuid4(),
    )

    rejected = gl_with_posting_support.process_instruction(kept)
    gl_with_posting_support.process_instruction(other)

    result = gl_with_posting_support.get_rejections(kept.producer_run_id)

    assert isinstance(result, DataFrame)
    rows = result.collect()
    assert len(rows) == 1
    assert UUID(rows[0]['GL_REJECTION_ID']) == rejected.rejection.gl_rejection_id
    assert UUID(rows[0]['PRODUCER_RUN_ID']) == kept.producer_run_id
