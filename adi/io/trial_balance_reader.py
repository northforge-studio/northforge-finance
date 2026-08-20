from pyspark.sql import DataFrame

from adi.io import CsvTableStore
from adi.config import SOURCE_DIR
from adi.contracts import TRIAL_BALANCE_SOURCE_SCHEMA


class TrialBalanceReader:
    def __init__(self, store: CsvTableStore):
        self.store = store


    def read(self) -> DataFrame:
        return self.store.read(
            SOURCE_DIR / 'trial_balance_source.csv',
            schema=TRIAL_BALANCE_SOURCE_SCHEMA,
        )

