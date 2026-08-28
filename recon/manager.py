from datetime import datetime, timezone
from uuid import UUID, uuid4

from pyspark.sql import DataFrame, Row

from core.runs import RunTracker

from gl import GLClient

from recon.calculation import calculate_recon
from recon.models import ReconResult, ReconRunResult
from recon.repository import ReconRepository


# v1 supports only TRIAL_BALANCE. Recon may need to consume multiple
# dataclasses/workflow_run_ids once more dataclasses exist; that is
# intentionally out of scope for now.
_SUPPORTED_DATACLASSES = frozenset({'TRIAL_BALANCE'})


class ReconManager:
    def __init__(
        self,
        repository: ReconRepository,
        run_tracker: RunTracker,
        gl: GLClient,
    ):
        self._repository = repository
        self._run_tracker = run_tracker
        self._gl = gl


    def reconcile(self, workflow_run_id: UUID) -> ReconRunResult:
        workflow = self._run_tracker.get_workflow_run(workflow_run_id)

        if workflow.dataclass not in _SUPPORTED_DATACLASSES:
            raise ValueError(
                f'Unsupported dataclass for recon: {workflow.dataclass!r}'
            )

        execution = self._run_tracker.start_execution(
            workflow_run_id=workflow_run_id,
            component='recon',
            operation='reconcile',
        )

        try:
            interface_df = self._repository.get_interface_trial_balance(workflow_run_id)
            gl_df = self._gl.get_postings(workflow_run_id)

            calculated_rows = calculate_recon(interface_df, gl_df).collect()

            results = tuple(
                self._to_result(row, workflow_run_id, execution.run_id)
                for row in calculated_rows
            )

            self._repository.write_results(results)
        except Exception:
            self._run_tracker.fail_execution(execution.run_id)
            raise

        self._run_tracker.complete_execution(execution.run_id)

        break_count = sum(
            1 for result in results if result.difference_amount != 0
        )

        return ReconRunResult(
            workflow_run_id=workflow_run_id,
            producer_run_id=execution.run_id,
            result_count=len(results),
            break_count=break_count,
            results=results,
        )


    def get_results(self, workflow_run_id: UUID) -> DataFrame:
        return self._repository.get_results(workflow_run_id)


    def _to_result(
        self,
        row: Row,
        workflow_run_id: UUID,
        producer_run_id: UUID,
    ) -> ReconResult:
        return ReconResult(
            recon_result_id=uuid4(),
            reconciled_at=datetime.now(timezone.utc),
            workflow_run_id=workflow_run_id,
            producer_run_id=producer_run_id,
            as_of_date=row['AS_OF_DATE'],
            entity_cd=row['ENTITY_CD'],
            dept_cd=row['DEPT_CD'],
            branch_cd=row['BRANCH_CD'],
            gl_account=row['GL_ACCOUNT'],
            sub_account=row['SUB_ACCOUNT'],
            affiliate_cd=row['AFFILIATE_CD'],
            product_cd=row['PRODUCT_CD'],
            book_cd=row['BOOK_CD'],
            source_cd=row['SOURCE_CD'],
            accounted_currency=row['ACCOUNTED_CURRENCY'],
            interface_balance=row['INTERFACE_BALANCE'],
            gl_balance=row['GL_BALANCE'],
            difference_amount=row['DIFFERENCE_AMOUNT'],
        )
