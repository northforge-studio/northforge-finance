from pyspark.sql import DataFrame
from pyspark.sql.types import StringType

from adi.contracts import (
    TRIAL_BALANCE_SOURCE_SCHEMA,
    TRIAL_BALANCE_STAGING_SCHEMA,
)
from adi.io.store import Store


class TrialBalanceRepository:
    def __init__(self, store: Store):
        self.store = store


    def read_source(self) -> DataFrame:
        return self.store.read(
            table_name='TRIAL_BALANCE_SOURCE',
            schema=TRIAL_BALANCE_SOURCE_SCHEMA,
        )


    def read_staging(self) -> DataFrame:
        return self.store.read(
            table_name='TRIAL_BALANCE_STAGING',
            schema=TRIAL_BALANCE_STAGING_SCHEMA,
        )


    def write_staging(self, df: DataFrame) -> None:
        self.store.write(
            df=df,
            table_name='TRIAL_BALANCE_STAGING',
        )
    