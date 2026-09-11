from pathlib import Path

from pyspark.sql import SparkSession, DataFrame

from core.store import (
    CsvStore,
    PostgresStore
)

from reference.models import ReferenceData
from reference.manager import ReferenceManager
from reference.repository import ReferenceRepository


class ReferenceClient:
    def __init__(self, repository: ReferenceRepository):
        self._repository = repository
        self._manager = ReferenceManager(repository)


    @classmethod
    def from_csv(
        cls,
        spark: SparkSession,
        fx_rate_path: str | Path,
        counterparty_path: str | Path,
    ) -> 'ReferenceClient':
        store = CsvStore(
            spark=spark,
            table_locations={
                ReferenceData.FX_RATE: Path(fx_rate_path),
                ReferenceData.COUNTERPARTY: Path(counterparty_path),
            },
        )

        return cls(ReferenceRepository(store))


    @classmethod
    def from_db(
        cls,
        spark: SparkSession,
        fx_rate_table: str | Path,
        counterparty_table: str | Path,
    ) -> 'ReferenceClient':
        store = PostgresStore(
            spark=spark,
            table_names={
                ReferenceData.FX_RATE: fx_rate_table,
                ReferenceData.COUNTERPARTY: counterparty_table,
            },
        )

        return cls(ReferenceRepository(store))


    def enrich_reference_data(self, df: DataFrame, reference_data: ReferenceData) -> DataFrame:
        return self._manager.enrich_reference_data(df, reference_data)
