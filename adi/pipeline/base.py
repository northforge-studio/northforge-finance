from abc import ABC, abstractmethod

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType


class BasePipeline(ABC):
    def run(self, df: DataFrame) -> DataFrame:
        df = self.staging(df)
        df = self.enrichment(df)
        df = self.posting(df)

        return df


    def staging(self, df: DataFrame) -> DataFrame:
        df = self.pre_staging(df)
        df = self.main_staging(df)
        df = self.post_staging(df)

        return df


    def enrichment(self, df: DataFrame) -> DataFrame:
        df = self.pre_enrichment(df)
        df = self.main_enrichment(df)
        df = self.post_enrichment(df)

        return df


    def posting(self, df: DataFrame) -> DataFrame:
        df = self.pre_posting(df)
        df = self.main_posting(df)
        df = self.post_posting(df)

        return df


    @abstractmethod
    def pre_staging(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def main_staging(self, df: DataFrame) -> DataFrame:
        ...


    @abstractmethod
    def post_staging(self, df: DataFrame) -> DataFrame:
        ...


    def pre_enrichment(self, df: DataFrame) -> DataFrame:
        return df


    def main_enrichment(self, df: DataFrame) -> DataFrame:
        return df


    def post_enrichment(self, df: DataFrame) -> DataFrame:
        return df


    def pre_posting(self, df: DataFrame) -> DataFrame:
        return df


    def main_posting(self, df: DataFrame) -> DataFrame:
        return df


    def post_posting(self, df: DataFrame) -> DataFrame:
        return df


    def _add_row_id(self, df: DataFrame) -> DataFrame:
        return (
            df.coalesce(1)
            .withColumn(
                'ROW_ID', 
                (F.monotonically_increasing_id() + 1).cast('string')
            )
        )


    def _align_to_schema(
        self,
        df: DataFrame,
        schema: StructType,
    ) -> DataFrame:
        columns = [
            field.name
            for field in schema.fields
        ]

        return df.select(*columns)
