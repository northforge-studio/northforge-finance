from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType, StringType


class CsvStore:
    def __init__(
        self,
        spark: SparkSession,
        table_paths: dict[str, Path],
    ):
        self.spark = spark
        self.table_paths = table_paths


    def read(
        self,
        table_name: str,
        schema: StructType | None = None,
    ) -> DataFrame:
        path = self.table_paths[table_name]

        reader = (
            self.spark.read
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
        mode: str = 'overwrite',
    ) -> None:
        path = self.table_paths[table_name]

        (
            df.write
            .mode(mode)
            .option('header', True)
            .csv(str(path))
        )
