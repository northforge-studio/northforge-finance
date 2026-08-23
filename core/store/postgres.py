from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType

from core.db import PostgresConfig, PostgresExecutor


class PostgresStore:
    def __init__(
        self,
        spark: SparkSession,
        config: PostgresConfig,
        table_locations: dict[str, str],
    ):
        self._spark = spark
        self._config = config
        self._table_locations = table_locations
        self._executor = PostgresExecutor(config)


    def _resolve(self, table_name: str) -> str:
        try:
            return self._table_locations[table_name]
        except KeyError:
            raise KeyError(f'Unknown table: {table_name!r}') from None


    def read(
        self,
        table_name: str,
        schema: StructType | None = None,
    ) -> DataFrame:
        physical_table = self._resolve(table_name)

        return (
            self._spark.read
            .jdbc(
                url=self._config.jdbc_url,
                table=physical_table,
                properties=self._config.jdbc_properties,
            )
        )


    def write(
        self,
        df: DataFrame,
        table_name: str,
        mode: str = 'append',
    ) -> None:
        physical_table = self._resolve(table_name)

        (
            df.write
            .jdbc(
                url=self._config.jdbc_url,
                table=physical_table,
                mode=mode,
                properties=self._config.jdbc_properties,
            )
        )


    def delete(
        self,
        table_name: str,
        filters: dict[str, Any],
        schema: StructType | None = None,
    ) -> None:
        if not filters:
            raise ValueError('delete requires at least one filter')

        physical_table = self._resolve(table_name)

        conditions = []

        parameters = {}

        for index, (column, value) in enumerate(filters.items()):
            parameter_name = f'value_{index}'

            conditions.append(
                f'"{column}" = :{parameter_name}'
            )

            parameters[parameter_name] = value

        where_clause = ' AND '.join(conditions)

        sql = (
            f'DELETE FROM {physical_table} '
            f'WHERE {where_clause}'
        )

        self._executor.execute(
            sql,
            parameters,
        )
