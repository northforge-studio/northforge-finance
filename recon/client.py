from pathlib import Path
from uuid import UUID

from pyspark.sql import DataFrame, SparkSession

from core.store import (
    CsvStore,
    PostgresStore,
)
from core.runs import RunTracker

from gl import GLClient

from recon.manager import ReconManager
from recon.models import ReconRunResult
from recon.repository import ReconRepository


class ReconClient:
    def __init__(
        self,
        repository: ReconRepository,
        run_tracker: RunTracker,
        gl: GLClient,
    ):
        self._repository = repository
        self._run_tracker = run_tracker
        self._gl = gl
        self._manager = ReconManager(repository, run_tracker, gl)


    @classmethod
    def from_csv(
        cls,
        spark: SparkSession,
        run_tracker: RunTracker,
        gl: GLClient,
        result_path: str | Path | None = None,
        interface_trial_balance_path: str | Path | None = None,
    ) -> 'ReconClient':
        table_locations = {}
        if result_path is not None:
            table_locations['RESULT'] = Path(result_path)
        if interface_trial_balance_path is not None:
            table_locations['INTERFACE_TRIAL_BALANCE'] = Path(
                interface_trial_balance_path
            )

        store = CsvStore(
            spark=spark,
            table_locations=table_locations,
        )

        return cls(ReconRepository(store, spark), run_tracker, gl)


    @classmethod
    def from_db(
        cls,
        spark: SparkSession,
        run_tracker: RunTracker,
        gl: GLClient,
        result_table: str = 'recon.result',
        interface_trial_balance_table: str = 'interface.trial_balance',
    ) -> 'ReconClient':
        store = PostgresStore(
            spark=spark,
            table_names={
                'RESULT': result_table,
                'INTERFACE_TRIAL_BALANCE': interface_trial_balance_table,
            },
        )

        return cls(ReconRepository(store, spark), run_tracker, gl)


    def reconcile(self, workflow_run_id: UUID) -> ReconRunResult:
        return self._manager.reconcile(workflow_run_id)


    def get_results(self, workflow_run_id: UUID) -> DataFrame:
        return self._manager.get_results(workflow_run_id)
