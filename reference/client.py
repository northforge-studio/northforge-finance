from pathlib import Path

from pyspark.sql import SparkSession, DataFrame

from core.store import CsvStore

from reference.manager import ReferenceManager
from reference.repository import (
    CsvRepository,
    Repository,
)


class ReferenceClient:
    def __init__(self, repository: Repository):
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
            table_paths={
                'REF_FX_RATE': Path(fx_rate_path),
                'REF_COUNTERPARTY': Path(counterparty_path),
            },
        )

        return cls(CsvRepository(store))


    def enrich_fx_rate(self, df: DataFrame) -> DataFrame:
        return self._manager.enrich_fx_rate(df)


    def enrich_counterparty(self, df: DataFrame) -> DataFrame:
        return self._manager.enrich_counterparty(df)
