from pyspark.sql import DataFrame
from pyspark.sql.types import StructType

from core.store import Store

from reference.contracts import (
    FX_RATE_SCHEMA,
    COUNTERPARTY_SCHEMA,
)
from reference.models import ReferenceData


class ReferenceRepository:
    def __init__(self, store: Store):
        self._store = store


    def get_reference_data(self, reference_data: ReferenceData) -> DataFrame:
        schema: StructType = None

        if reference_data == ReferenceData.FX_RATE:
            schema = FX_RATE_SCHEMA
        elif reference_data == ReferenceData.COUNTERPARTY:
            schema = COUNTERPARTY_SCHEMA
        else:
            raise ValueError(f"Unsupported reference data: {reference_data}")

        return self._store.read(
            table_name=reference_data,
            schema=schema,
        )
