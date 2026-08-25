from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from spec.repository import SpecRepository


class SpecManager:
    def __init__(self, repository: SpecRepository):
        self._repository = repository


    def apply_transformation(
        self,
        df: DataFrame,
        dataclass: str,
        zone: str,
        stage: str,
        sub_stage: str = '',
    ) -> DataFrame:
        transformations = self._repository.get_transformations(
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


    def apply_file_layout(
        self,
        df: DataFrame,
        dataclass: str
    ) -> DataFrame:
        expressions = self._repository.get_file_layout_expressions(dataclass=dataclass)

        return df.selectExpr(*expressions)
