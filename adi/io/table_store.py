from pathlib import Path

from pyspark.sql import DataFrame, SparkSession


class CsvTableStore:
    def __init__(self, spark: SparkSession):
        self.spark = spark

    def read(self, path: Path) -> DataFrame:
        return (
            self.spark.read
            .option('header', True)
            .option('inferSchema', True)
            .csv(str(path))
        )

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
