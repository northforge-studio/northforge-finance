from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from pyspark.sql import functions as F

from recon.contracts import RESULT_SCHEMA

from break_analysis.services.recon import ReconBreakRecordResolver

from tests.support.constants import AS_OF_DATE


class _FakeReconClient:
    '''Mirrors ReconClient.get_results(): scoped to the given workflow_run_id.'''

    def __init__(self, df):
        self._df = df

    def get_results(self, workflow_run_id):
        return self._df.filter(
            F.col('WORKFLOW_RUN_ID') == str(workflow_run_id)
        )


def _result_row(**overrides) -> dict:
    row = dict(
        RECON_RESULT_ID=str(uuid4()),
        RECONCILED_AT=datetime.now(timezone.utc),
        WORKFLOW_RUN_ID=str(uuid4()),
        PRODUCER_RUN_ID=str(uuid4()),
        AS_OF_DATE=AS_OF_DATE,
        ENTITY_CD='USM',
        BRANCH_CD='100',
        DEPT_CD='4000',
        GL_ACCOUNT='123456',
        SUB_ACCOUNT='001',
        AFFILIATE_CD='AFF1',
        PRODUCT_CD='PRD1',
        BOOK_CD='BK1',
        SOURCE_CD='SRC1',
        ACCOUNTED_CURRENCY='USD',
        INTERFACE_BALANCE=Decimal('100.00'),
        GL_BALANCE=Decimal('100.00'),
        DIFFERENCE_AMOUNT=Decimal('0.00'),
    )
    row.update(overrides)
    return row


def _results_df(spark, rows: list[dict]):
    return spark.createDataFrame(
        [tuple(row[field.name] for field in RESULT_SCHEMA.fields) for row in rows],
        schema=RESULT_SCHEMA,
    )


def test_matching_result_returns_expected_break_record(spark):
    workflow_run_id = uuid4()
    row = _result_row(WORKFLOW_RUN_ID=str(workflow_run_id))
    df = _results_df(spark, [row])
    resolver = ReconBreakRecordResolver(_FakeReconClient(df))

    record = resolver.get_break_record(
        workflow_run_id=workflow_run_id,
        recon_result_id=row['RECON_RESULT_ID'],
    )

    assert str(record.recon_result_id) == row['RECON_RESULT_ID']
    assert record.workflow_run_id == workflow_run_id
    assert record.as_of_date == AS_OF_DATE
    assert record.segments.entity_cd == 'USM'
    assert record.segments.sub_account == '001'
    assert record.accounted_currency == 'USD'
    assert record.interface_balance == Decimal('100.00')
    assert record.gl_balance == Decimal('100.00')
    assert record.difference_amount == Decimal('0.00')


def test_missing_recon_result_id_raises(spark):
    workflow_run_id = uuid4()
    row = _result_row(WORKFLOW_RUN_ID=str(workflow_run_id))
    df = _results_df(spark, [row])
    resolver = ReconBreakRecordResolver(_FakeReconClient(df))

    with pytest.raises(ValueError, match='No recon.result row found'):
        resolver.get_break_record(
            workflow_run_id=workflow_run_id,
            recon_result_id=uuid4(),
        )


def test_duplicate_recon_result_id_raises(spark):
    workflow_run_id = uuid4()
    recon_result_id = str(uuid4())
    rows = [
        _result_row(WORKFLOW_RUN_ID=str(workflow_run_id), RECON_RESULT_ID=recon_result_id),
        _result_row(WORKFLOW_RUN_ID=str(workflow_run_id), RECON_RESULT_ID=recon_result_id),
    ]
    df = _results_df(spark, rows)
    resolver = ReconBreakRecordResolver(_FakeReconClient(df))

    with pytest.raises(ValueError, match='Multiple recon.result rows found'):
        resolver.get_break_record(
            workflow_run_id=workflow_run_id,
            recon_result_id=recon_result_id,
        )
