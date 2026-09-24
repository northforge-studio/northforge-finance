from decimal import Decimal

import pytest

from core.store import CsvStore

from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA, POSTING_SCHEMA

from recon import ReconClient
from recon.models import ReconRunResult
from recon.repository import ReconRepository

from tests.recon.factories import make_interface_values, make_posting_values
from tests.recon.fakes import FakeGL
from tests.support.constants import BUSINESS_DT


def test_from_csv_reconciles_and_persists_through_a_real_repository(
    spark, tmp_path, run_tracker, workflow,
):
    interface_store = CsvStore(
        spark=spark,
        table_locations={
            'INTERFACE_TRIAL_BALANCE': tmp_path / 'INTERFACE_TRIAL_BALANCE',
        },
    )
    interface_df = spark.createDataFrame(
        [make_interface_values(workflow.workflow_run_id)],
        schema=INTERFACE_TRIAL_BALANCE_SCHEMA,
    )
    interface_store.write(interface_df, table_name='INTERFACE_TRIAL_BALANCE')

    gl_df = spark.createDataFrame(
        [make_posting_values(workflow.workflow_run_id)],
        schema=POSTING_SCHEMA,
    )
    gl = FakeGL({workflow.workflow_run_id: gl_df})

    client = ReconClient.from_csv(
        spark=spark,
        run_tracker=run_tracker,
        gl=gl,
        result_path=tmp_path / 'RESULT',
        interface_trial_balance_path=tmp_path / 'INTERFACE_TRIAL_BALANCE',
    )

    result = client.reconcile(workflow.workflow_run_id)

    assert isinstance(result, ReconRunResult)
    assert result.result_count == 1
    assert result.break_count == 0

    # Read back through a fresh ReconRepository against the same CSV
    # store, to prove the client's write actually reached persistence.
    verify_store = CsvStore(
        spark=spark,
        table_locations={'RESULT': tmp_path / 'RESULT'},
    )
    persisted = ReconRepository(verify_store, spark).get_results(
        workflow.workflow_run_id
    ).collect()

    assert len(persisted) == 1
    assert persisted[0]['WORKFLOW_RUN_ID'] == str(workflow.workflow_run_id)
    assert persisted[0]['PRODUCER_RUN_ID'] == str(result.producer_run_id)
    assert persisted[0]['DIFFERENCE_AMOUNT'] == Decimal('0.00')

    # The client's own get_results() (not just a fresh ReconRepository)
    # reads back the same persisted row.
    via_client = client.get_results(workflow.workflow_run_id).collect()
    assert len(via_client) == 1
    assert via_client[0]['WORKFLOW_RUN_ID'] == str(workflow.workflow_run_id)


def test_reconcile_raises_for_an_unsupported_dataclass(spark, tmp_path, run_tracker):
    workflow = run_tracker.start_workflow(dataclass='POSITION', business_dt=BUSINESS_DT)

    client = ReconClient.from_csv(
        spark=spark,
        run_tracker=run_tracker,
        gl=FakeGL({}),
        result_path=tmp_path / 'RESULT',
        interface_trial_balance_path=tmp_path / 'INTERFACE_TRIAL_BALANCE',
    )

    with pytest.raises(ValueError, match='POSITION'):
        client.reconcile(workflow.workflow_run_id)
