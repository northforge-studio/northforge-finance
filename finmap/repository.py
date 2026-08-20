import csv
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from finmap.models import (
    FieldType,
    LookupType,
    Mapping,
    MappingDefinition,
    MappingField,
)


class CsvMappingRepository:
    def __init__(
        self,
        spark: SparkSession,
        metadata_path: str | Path,
        data_path: str | Path,
    ):
        self._spark = spark
        self._metadata_path = Path(metadata_path)
        self._data_path = Path(data_path)


    def get_mapping(self, mapping_name: str) -> Mapping:
        definition = self.get_definition(mapping_name)
        data = self._read_mapping_data(definition)

        return Mapping(
            definition=definition,
            data=data,
        )
    

    def get_definition(self, mapping_name: str) -> MappingDefinition:
        rows = self._read_metadata(mapping_name)

        if not rows:
            raise KeyError(f'Mapping not found: {mapping_name}')

        mapping_data_names = {
            row['MAPPING_DATA_NAME']
            for row in rows
        }

        if len(mapping_data_names) != 1:
            raise ValueError(
                f'Mapping {mapping_name!r} has multiple '
                f'MAPPING_DATA_NAME values: {mapping_data_names}'
            )

        fields = tuple(
            MappingField(
                physical_name=row['METADATA_FIELD_NAME'],
                logical_name=row['LOGICAL_FIELD_NAME'],
                field_type=FieldType(row['FIELD_TYPE']),
                lookup_type=LookupType(row['LOOKUP_TYPE']),
                src_field_name=row['SRC_FIELD_NAME'],
                datatype=row['DATATYPE'],
                order=int(row['UI_FIELD_ORDER']),
            )
            for row in sorted(
                rows,
                key=lambda row: int(row['UI_FIELD_ORDER']),
            )
        )

        return MappingDefinition(
            mapping_name=mapping_name,
            mapping_data_name=next(iter(mapping_data_names)),
            fields=fields,
        )


    def _read_metadata(self, mapping_name: str) -> list[dict[str, str]]:
        with self._metadata_path.open(
            mode='r',
            encoding='utf-8-sig',
            newline='',
        ) as file:
            reader = csv.DictReader(file)

            return [
                row
                for row in reader
                if row['MAPPING_NAME'] == mapping_name
            ]


    def _read_mapping_data(
        self,
        definition: MappingDefinition,
    ):
        df = (
            self._spark.read
            .option('header', True)
            .csv(str(self._data_path))
            .filter(
                F.col('MAPPING_NAME') == definition.mapping_name
            )
        )

        columns = [
            F.col(field.physical_name).alias(field.logical_name)
            for field in definition.fields
        ]

        return df.select(*columns)
