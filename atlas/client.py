from pathlib import Path

from pyspark.sql import SparkSession, DataFrame

from core.store import (
    CsvStore,
    PostgresStore
)

from atlas.manager import MappingManager
from atlas.models import (
    GatewayRule,
    Mapping,
    MappingDefinition,
    MappingResolutionEvidence,
)
from atlas.repository import AtlasRepository


class AtlasClient:
    def __init__(self, repository: AtlasRepository):
        self._repository = repository
        self._manager = MappingManager(repository)


    @classmethod
    def from_csv(
        cls,
        spark: SparkSession,
        metadata_path: str | Path,
        data_path: str | Path,
    ) -> 'AtlasClient':
        store = CsvStore(
            spark=spark,
            table_locations={
                'MAPPING_META': Path(metadata_path),
                'MAPPING_DATA': Path(data_path),
            },
        )

        return cls(AtlasRepository(store))


    @classmethod
    def from_db(
        cls,
        spark: SparkSession,
        metadata_table: str | Path,
        data_table: str | Path,
    ) -> 'AtlasClient':
        store = PostgresStore(
            spark=spark,
            table_names={
                'MAPPING_META': metadata_table,
                'MAPPING_DATA': data_table,
            },
        )

        return cls(AtlasRepository(store))


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


    def explain_resolution(
        self,
        mapping_name: str,
        input_values: dict[str, str],
    ) -> MappingResolutionEvidence:
        return self._manager.explain_resolution(
            mapping_name,
            input_values=input_values,
        )
