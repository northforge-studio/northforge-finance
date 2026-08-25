from typing import Any

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructType
from pyspark.sql import DataFrame, SparkSession

from core.db import PostgresConfig, PostgresExecutor


class PostgresStore:
    def __init__(
        self,
        spark: SparkSession,
        table_names: dict[str, str],
    ):
        self._spark = spark
        self._config = PostgresConfig.from_env()
        self._table_names = table_names
        self._executor = PostgresExecutor(self._config)


    def _resolve(self, table_name: str) -> str:
        try:
            return self._table_names[table_name]
        except KeyError:
            raise KeyError(f'Unknown table: {table_name!r}') from None


    def read(
        self,
        table_name: str,
        schema: StructType | None = None,
    ) -> DataFrame:
        physical_table = self._resolve(table_name)

        df = (
            self._spark.read
            .jdbc(
                url=self._config.jdbc_url,
                table=physical_table,
                properties=self._config.jdbc_properties,
            )
        )

        if schema is not None:
            df = self._normalize_columns(df, schema)

        return df


    def write(
        self,
        df: DataFrame,
        table_name: str,
        mode: str = 'append',
    ) -> None:
        physical_table = self._resolve(table_name)

        df = self._to_physical_columns(df)
        df = self._fill_null_strings(df)

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
                f'"{column.lower()}" = :{parameter_name}'
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


    def _normalize_columns(
        self,
        df: DataFrame,
        schema: StructType,
    ) -> DataFrame:
        actual_columns = {
            column.lower(): column
            for column in df.columns
        }

        expressions = []

        for field in schema.fields:
            actual_name = actual_columns.get(field.name.lower())

            if actual_name is None:
                raise ValueError(
                    f'Expected column {field.name!r} '
                    f'not found in table. '
                    f'Available columns: {df.columns}'
                )

            expressions.append(
                F.col(actual_name).alias(field.name)
            )

        return df.select(*expressions)


    def _to_physical_columns(self, df: DataFrame) -> DataFrame:
        return df.toDF(*[
            column.lower()
            for column in df.columns
        ])


    def _fill_null_strings(self, df: DataFrame) -> DataFrame:
        string_columns = [
            field.name
            for field in df.schema.fields
            if isinstance(field.dataType, StringType)
        ]

        if not string_columns:
            return df

        return df.fillna('', subset=string_columns)
