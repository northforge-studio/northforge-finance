from uuid import UUID

from pyspark.sql import Row
from pyspark.sql import functions as F

from break_analysis.models import BreakRecord
from gl.models import GLSegments
from recon.client import ReconClientProtocol


class ReconBreakRecordResolver:
    def __init__(self, recon_client: ReconClientProtocol):
        self._recon = recon_client

    def get_break_record(
        self,
        workflow_run_id: UUID,
        recon_result_id: UUID,
    ) -> BreakRecord:
        results_df = self._recon.get_results(workflow_run_id)

        rows = results_df.filter(
            F.col('RECON_RESULT_ID') == str(recon_result_id)
        ).collect()

        if not rows:
            raise ValueError(
                f'No recon.result row found for recon_result_id='
                f'{recon_result_id} in workflow_run_id={workflow_run_id}.'
            )

        if len(rows) > 1:
            raise ValueError(
                f'Multiple recon.result rows found for recon_result_id='
                f'{recon_result_id} in workflow_run_id={workflow_run_id}; '
                f'expected exactly one.'
            )

        return self._to_break_record(rows[0])

    def _to_break_record(self, row: Row) -> BreakRecord:
        return BreakRecord(
            recon_result_id=UUID(row['RECON_RESULT_ID']),
            workflow_run_id=UUID(row['WORKFLOW_RUN_ID']),
            as_of_date=row['AS_OF_DATE'],
            segments=GLSegments(
                entity_cd=row['ENTITY_CD'],
                branch_cd=row['BRANCH_CD'],
                dept_cd=row['DEPT_CD'],
                gl_account=row['GL_ACCOUNT'],
                sub_account=row['SUB_ACCOUNT'],
                affiliate_cd=row['AFFILIATE_CD'],
                product_cd=row['PRODUCT_CD'],
                book_cd=row['BOOK_CD'],
                source_cd=row['SOURCE_CD'],
            ),
            accounted_currency=row['ACCOUNTED_CURRENCY'],
            interface_balance=row['INTERFACE_BALANCE'],
            gl_balance=row['GL_BALANCE'],
            difference_amount=row['DIFFERENCE_AMOUNT'],
        )
