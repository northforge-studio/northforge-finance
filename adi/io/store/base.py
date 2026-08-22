from typing import Any, Protocol

from pyspark.sql import DataFrame
from pyspark.sql.types import StructType


class Store(Protocol):
    def read(
        self,
        table_name: str,
        schema: StructType | None = None,
    ) -> DataFrame:
        ...


    def write(
        self,
        df: DataFrame,
        table_name: str,
        mode: str = 'overwrite',
    ) -> None:
        ...


    def delete(
        self,
        table_name: str,
        filters: dict[str, Any],
        schema: StructType | None = None,
    ) -> None:
        ...
