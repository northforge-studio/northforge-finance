from typing import Any, Protocol

from pyspark.sql import DataFrame
from pyspark.sql.types import StringType, StructType


def fill_null_strings(df: DataFrame) -> DataFrame:
    string_columns = [
        field.name
        for field in df.schema.fields
        if isinstance(field.dataType, StringType)
    ]

    if not string_columns:
        return df

    return df.fillna('', subset=string_columns)


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
        mode: str = 'append',
    ) -> None:
        ...


    def delete(
        self,
        table_name: str,
        filters: dict[str, Any],
        schema: StructType | None = None,
    ) -> None:
        ...
