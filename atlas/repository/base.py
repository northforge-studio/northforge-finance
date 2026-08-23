from typing import Protocol

from atlas.models import (
    Mapping,
    MappingDefinition,
)


class Repository(Protocol):
    def get_definition(self, mapping_name: str) -> MappingDefinition:
            ...

    
    def get_mapping(self, mapping_name: str) -> Mapping:
        ...
