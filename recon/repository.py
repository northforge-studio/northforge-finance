from typing import Sequence
from uuid import UUID

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from core.store import Store

from recon.contracts import RESULT_SCHEMA
from recon.models import ReconResult


class ReconRepository:
    def __init__(self, store: Store, spark: SparkSession):
        self._store = store
        self._spark = spark


    def write_results(self, results: Sequence[ReconResult]) -> None:
        if not results:
            return

        df = self._spark.createDataFrame(
            [self._to_row(result) for result in results],
            schema=RESULT_SCHEMA,
        )

        self._store.write(df, table_name='RESULT')


    def get_results(
        self,
        workflow_run_id: UUID,
    ) -> DataFrame:
        df = self._store.read(
            table_name='RESULT',
            schema=RESULT_SCHEMA,
        )

        return df.filter(F.col('WORKFLOW_RUN_ID') == str(workflow_run_id))


    def _to_row(self, result: ReconResult) -> tuple:
        return (
            str(result.recon_result_id),
            result.reconciled_at,
            str(result.workflow_run_id),
            str(result.producer_run_id),
            result.as_of_date,
            result.entity_cd,
            result.dept_cd,
            result.branch_cd,
            result.gl_account,
            result.sub_account,
            result.affiliate_cd,
            result.product_cd,
            result.book_cd,
            result.source_cd,
            result.accounted_currency,
            result.interface_balance,
            result.gl_balance,
            result.difference_amount,
        )
