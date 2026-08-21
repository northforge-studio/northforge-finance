from pathlib import Path

from pyspark.sql import SparkSession, DataFrame

from finmap.manager import MappingManager
from finmap.models import Mapping, MappingDefinition
from finmap.repository import (
    CsvRepository,
    Repository,
)


class FinMapClient:
    def __init__(self, repository: Repository):
        self._repository = repository
        self._manager = MappingManager(repository)


    @classmethod
    def from_csv(
        cls,
        spark: SparkSession,
        metadata_path: str | Path,
        data_path: str | Path,
    ) -> 'FinMapClient':
        repository = CsvRepository(
            spark=spark,
            metadata_path=metadata_path,
            data_path=data_path,
        )

        return cls(repository)


    def apply(
        self,
        df: DataFrame,
        mapping_name: str,
    ) -> DataFrame:
        return self._manager.apply(
            df=df,
            mapping_name=mapping_name,
        )


    def get_mapping(
        self,
        mapping_name: str,
    ) -> Mapping:
        return self._repository.get_mapping(
            mapping_name
        )


    def get_definition(
        self,
        mapping_name: str,
    ) -> MappingDefinition:
        return self._repository.get_definition(
            mapping_name
        )
