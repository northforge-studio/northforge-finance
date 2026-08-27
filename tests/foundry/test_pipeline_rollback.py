from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

from core.runs import RunIdentity
from foundry.pipeline.trial_balance import TrialBalancePipeline
from foundry.repository import TrialBalanceRepository


def _make_pipeline(repository):
    return TrialBalancePipeline(
        business_dt=date(2026, 8, 24),
        atlas=MagicMock(),
        repository=repository,
        reference=MagicMock(),
        spec=MagicMock(),
    )


def test_rollback_execution_deletes_only_the_named_operations_rows():
    repository = MagicMock(spec=TrialBalanceRepository)
    pipeline = _make_pipeline(repository)

    identity = RunIdentity(
        workflow_run_id=uuid4(),
        run_id=uuid4(),
        parent_run_id=uuid4(),
    )

    pipeline.rollback_execution('STAGING', identity)

    repository.delete_staging.assert_called_once_with(identity.run_id)
    repository.delete_enrichment.assert_not_called()
    repository.delete_reporting.assert_not_called()
    repository.delete_posting.assert_not_called()
    repository.delete_interface.assert_not_called()


def test_rollback_execution_dispatches_each_operation_to_its_own_delete():
    repository = MagicMock(spec=TrialBalanceRepository)
    pipeline = _make_pipeline(repository)

    operations_and_handlers = {
        'STAGING': repository.delete_staging,
        'ENRICHMENT': repository.delete_enrichment,
        'REPORTING': repository.delete_reporting,
        'POSTING': repository.delete_posting,
        'INTERFACE': repository.delete_interface,
    }

    for operation, handler in operations_and_handlers.items():
        identity = RunIdentity(
            workflow_run_id=uuid4(), run_id=uuid4(), parent_run_id=None,
        )
        pipeline.rollback_execution(operation, identity)
        handler.assert_called_once_with(identity.run_id)


def test_rollback_execution_unknown_operation_is_a_no_op():
    repository = MagicMock(spec=TrialBalanceRepository)
    pipeline = _make_pipeline(repository)

    identity = RunIdentity(workflow_run_id=uuid4(), run_id=uuid4(), parent_run_id=None)

    pipeline.rollback_execution('BOGUS', identity)

    repository.delete_staging.assert_not_called()
    repository.delete_enrichment.assert_not_called()
    repository.delete_reporting.assert_not_called()
    repository.delete_posting.assert_not_called()
    repository.delete_interface.assert_not_called()


def test_repository_delete_methods_filter_by_producer_run_id_not_business_dt_or_batch():
    store = MagicMock()
    repository = TrialBalanceRepository(store)
    producer_run_id = uuid4()

    repository.delete_staging(producer_run_id)
    repository.delete_enrichment(producer_run_id)
    repository.delete_reporting(producer_run_id)
    repository.delete_posting(producer_run_id)
    repository.delete_interface(producer_run_id)

    for call in store.delete.call_args_list:
        filters = call.kwargs['filters']
        assert filters == {'PRODUCER_RUN_ID': str(producer_run_id)}
        assert 'BUSINESS_DT' not in filters
        assert 'BATCH_ID' not in filters
