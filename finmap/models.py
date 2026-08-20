from enum import StrEnum
from dataclasses import dataclass

from pyspark.sql import DataFrame


class FieldType(StrEnum):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    LOGICAL = 'LOGICAL'


class LookupType(StrEnum):
    VALUE = 'VALUE'
    INFORMATIONAL = 'INFORMATIONAL'


@dataclass(frozen=True)
class MappingField:
    physical_name: str
    logical_name: str
    field_type: FieldType
    lookup_type: LookupType
    src_field_name: str | None
    datatype: str
    order: int


    @property
    def is_lookup_field(self) -> bool:
        return (
            self.field_type == FieldType.INPUT
            and self.lookup_type == LookupType.VALUE
        )


@dataclass(frozen=True)
class MappingDefinition:
    mapping_name: str
    mapping_data_name: str
    fields: tuple[MappingField, ...]


    @property
    def input_fields(self) -> tuple[MappingField, ...]:
        return tuple(
            field
            for field in self.fields
            if field.field_type == FieldType.INPUT
        )


    @property
    def lookup_fields(self) -> tuple[MappingField, ...]:
        return tuple(
            field
            for field in self.fields
            if field.is_lookup_field
        )


    @property
    def informational_fields(self) -> tuple[MappingField, ...]:
        return tuple(
            field
            for field in self.fields
            if (
                field.field_type == FieldType.INPUT
                and field.lookup_type == LookupType.INFORMATIONAL
            )
        )


    @property
    def output_fields(self) -> tuple[MappingField, ...]:
        return tuple(
            field
            for field in self.fields
            if field.field_type == FieldType.OUTPUT
        )


    @property
    def logical_fields(self) -> tuple[MappingField, ...]:
        return tuple(
            field
            for field in self.fields
            if field.field_type == FieldType.LOGICAL
        )


@dataclass(frozen=True)
class Mapping:
    definition: MappingDefinition
    data: DataFrame
