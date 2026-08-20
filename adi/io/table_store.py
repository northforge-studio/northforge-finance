from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType


class CsvTableStore:
    def __init__(self, spark: SparkSession):
        self.spark = spark


    def read(
            self, 
            path: Path,
            schema: StructType | None = None,
        ) -> DataFrame:
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

        return reader.csv(str(path))


    def write(
        self,
        df: DataFrame,
        path: Path,
        mode: str = 'overwrite',
    ) -> None:
        (
            df.write
            .mode(mode)
            .option('header', True)
            .csv(str(path))
        )
