from pyspark.sql import DataFrame

from finmap.models import LookupType
from finmap.repository import CsvMappingRepository


class MappingManager:
    def __init__(self, repository: CsvMappingRepository):
        self._repository = repository


    def get_mapping(self, mapping_name: str):
        return self._repository.get_mapping(mapping_name)


    def validate_source_columns(
        self,
        df: DataFrame,
        mapping_name: str
    ) -> None:
        mapping = self.get_mapping(mapping_name)

        required_columns = {
            field.src_field_name 
            for field in mapping.definition.lookup_fields
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f'Mapping {mapping_name!r} requires source columns '
                f'{sorted(missing_columns)}'
            )
