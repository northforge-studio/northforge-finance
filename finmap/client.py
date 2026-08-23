from pathlib import Path

from pyspark.sql import SparkSession, DataFrame

from core.io.store import CsvStore

from finmap.manager import MappingManager
from finmap.models import Mapping, MappingDefinition, GatewayRule
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
        store = CsvStore(
            spark=spark,
            table_paths={
                'MAPPING_META': Path(metadata_path),
                'MAPPING_DATA': Path(data_path),
            },
        )

        return cls(CsvRepository(store))


    def apply(
        self,
        df: DataFrame,
        mapping_name: str,
    ) -> DataFrame:
        return self._manager.apply(
            df,
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


    def get_rule_config(
        self,
        dataclass: str,
    ) -> list[GatewayRule]:
        return self._manager.get_rule_config(
            dataclass
        )
