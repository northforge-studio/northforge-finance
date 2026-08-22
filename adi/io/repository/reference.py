from pyspark.sql import DataFrame

from adi.contracts import (
    FX_RATE_SCHEMA,
    COUNTERPARTY_SCHEMA,
)
from adi.io.store import Store


class ReferenceRepository:
    def __init__(self, store: Store):
        self.store = store


    def get_fx_rate(self) -> DataFrame:
        return self.store.read(
            table_name='REF_FX_RATE',
            schema=FX_RATE_SCHEMA,
        )


    def get_counterparty(self) -> DataFrame:
        return self.store.read(
            table_name='REF_COUNTERPARTY',
            schema=COUNTERPARTY_SCHEMA,
        )
