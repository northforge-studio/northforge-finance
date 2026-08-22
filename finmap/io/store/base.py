from typing import Protocol

from pyspark.sql import DataFrame
from pyspark.sql.types import StructType


class Store(Protocol):
    def read(
        self,
        table_name: str,
        schema: StructType | None = None,
    ) -> DataFrame:
        ...
