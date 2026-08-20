from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from adi.config import REFERENCE_DIR


class TransformationManager:
    TABLE_NAME = 'cfg_transformations.csv'

    def __init__(
        self,
        spark: SparkSession,
    ):
        self.spark = spark


    def get_transformations(
        self,
        dataclass: str,
        zone: str,
        stage: str,
    ) -> list[dict]:
        config_df = (
            self.spark.read
            .option('header', True)
            .option('inferSchema', True)
            .csv(str(REFERENCE_DIR / self.TABLE_NAME))
        )

        rows = (
            config_df
            .filter(
                (F.col('DATACLASS') == dataclass)
                & (F.col('ZONE') == zone)
                & (F.col('STAGE') == stage)
                & (F.col('STATUS') == 'A')
            )
            .orderBy('SEQ')
            .collect()
        )

        return [row.asDict() for row in rows]


    def apply(
        self,
        df: DataFrame,
        dataclass: str,
        zone: str,
        stage: str,
    ) -> DataFrame:
        transformations = self.get_transformations(
            dataclass=dataclass,
            zone=zone,
            stage=stage,
        )

        for transformation in transformations:
            df = df.withColumn(
                transformation['OUTPUT_COL_NAME'],
                F.expr(transformation['EXPRESSION']),
            )

        return df
