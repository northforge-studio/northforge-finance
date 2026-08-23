from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from adi.repository import TransformationRepository


class TransformationManager:
    def __init__(self, repository: TransformationRepository):
        self.repository = repository


    def apply(
        self,
        df: DataFrame,
        dataclass: str,
        zone: str,
        stage: str,
        sub_stage: str = '',
    ) -> DataFrame:
        transformations = self.repository.get_transformations(
            dataclass=dataclass,
            zone=zone,
            stage=stage,
            sub_stage=sub_stage,
        )

        for transformation in transformations:
            df = df.withColumn(
                transformation['OUTPUT_COL_NAME'],
                F.expr(transformation['EXPRESSION']),
            )

        return df
