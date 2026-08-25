from pathlib import Path

from pyspark.sql import SparkSession, DataFrame

from core.store import (
    CsvStore,
    PostgresStore
)

from spec.models import SpecType
from spec.manager import SpecManager
from spec.repository import SpecRepository


class SpecClient:
    def __init__(self, repository: SpecRepository):
        self._repository = repository
        self._manager = SpecManager(repository)


    @classmethod
    def from_csv(
        cls,
        spark: SparkSession,
        transformation_path: str | Path,
        file_layout_path: str | Path,
    ) -> 'SpecClient':
        store = CsvStore(
            spark=spark,
            table_locations={
                SpecType.TRANSFORMATION: Path(transformation_path),
                SpecType.FILE_LAYOUT: Path(file_layout_path),
            },
        )

        return cls(SpecRepository(store))


    @classmethod
    def from_db(
        cls,
        spark: SparkSession,
        transformation_table: str,
        file_layout_table: str,
    ) -> 'SpecClient':
        store = PostgresStore(
            spark=spark,
            table_names={
                SpecType.TRANSFORMATION: transformation_table,
                SpecType.FILE_LAYOUT: file_layout_table,
            },
        )

        return cls(SpecRepository(store))


    def apply_transformation(
        self,
        df: DataFrame,
        dataclass: str,
        zone: str,
        stage: str,
        sub_stage: str = '',
    ) -> DataFrame:
        return self._manager.apply_transformation(
            df,
            dataclass=dataclass,
            zone=zone,
            stage=stage,
            sub_stage=sub_stage,
        )


    def apply_file_layout(
        self,
        df: DataFrame,
        dataclass: str,
    ) -> DataFrame:
        return self._manager.apply_file_layout(
            df,
            dataclass,
        )
