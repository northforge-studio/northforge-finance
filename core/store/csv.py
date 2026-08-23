import shutil
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StringType


class CsvStore:
    def __init__(
        self,
        spark: SparkSession,
        table_locations: dict[str, Path],
    ):
        self._spark = spark
        self._table_locations = table_locations


    def _resolve(self, table_name: str) -> Path:
        try:
            return self._table_locations[table_name]
        except KeyError:
            raise KeyError(f'Unknown table: {table_name!r}') from None


    def read(
        self,
        table_name: str,
        schema: StructType | None = None,
    ) -> DataFrame:
        path = self._resolve(table_name)

        if schema is not None and not Path(path).exists():
            return self._spark.createDataFrame([], schema=schema)

        reader = (
            self._spark.read
            .option('header', True)
            .option('ignoreLeadingWhiteSpace', True)
            .option('ignoreTrailingWhiteSpace', True)
        )

        if schema is not None:
            reader = reader.schema(schema)
        else:
            reader = reader.option('inferSchema', True)

        df = reader.csv(str(path))

        if schema is not None:
            string_cols = [
                field.name
                for field in schema.fields
                if isinstance(field.dataType, StringType)
            ]

            df = df.fillna(
                '',
                subset=string_cols,
            )

        return df


    def write(
        self,
        df: DataFrame,
        table_name: str,
        mode: str = 'append',
    ) -> None:
        path = self._resolve(table_name)

        (
            df.write
            .mode(mode)
            .option('header', True)
            .csv(str(path))
        )


    def delete(
        self,
        table_name: str,
        filters: dict[str, Any],
        schema: StructType | None = None,
    ) -> None:
        if not filters:
            raise ValueError('delete requires at least one filter')

        path = Path(self._resolve(table_name))

        if not path.exists():
            return

        df = self.read(table_name, schema=schema)

        condition = F.lit(True)
        for column, value in filters.items():
            condition = condition & (F.col(column) == F.lit(value))

        remaining_df = df.filter(~condition)

        tmp_path = path.with_name(f'{path.name}.tmp')
        if tmp_path.exists():
            shutil.rmtree(tmp_path) if tmp_path.is_dir() else tmp_path.unlink()

        (
            remaining_df.write
            .mode('overwrite')
            .option('header', True)
            .csv(str(tmp_path))
        )

        shutil.rmtree(path) if path.is_dir() else path.unlink()
        tmp_path.rename(path)
