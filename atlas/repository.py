from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from core.store import Store

from atlas.models import (
    FieldType,
    LookupType,
    Mapping,
    MappingDefinition,
    MappingField,
)
from atlas.contracts import MAPPING_META_SCHEMA, MAPPING_DATA_SCHEMA


class AtlasRepository:
    def __init__(self, store: Store):
        self._store = store


    def get_mapping(self, mapping_name: str) -> Mapping:
        definition = self.get_definition(mapping_name)
        data = self._read_mapping_data(definition)

        return Mapping(
            definition=definition,
            data=self._fillna_mapping_columns(data, definition),
        )


    def get_mapping_details(self, mapping_name: str) -> Mapping:
        """Diagnostic counterpart to get_mapping(): includes inactive rows
        and each row's STATUS, so callers can explain how inputs would
        resolve. Not used by MappingManager.apply(), which stays
        active-only via get_mapping()."""
        definition = self.get_definition(mapping_name)
        data = self._read_mapping_data(
            definition,
            include_inactive=True,
            include_status=True,
        )

        return Mapping(
            definition=definition,
            data=self._fillna_mapping_columns(data, definition),
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
            mapping_name=mapping_name.upper(),
            mapping_data_name=next(iter(mapping_data_names)),
            fields=fields,
        )


    def _read_metadata(self, mapping_name: str) -> list[dict[str, str]]:
        df = self._store.read('MAPPING_META', schema=MAPPING_META_SCHEMA)

        rows = (
            df
            .filter(
                F.upper(F.col('MAPPING_NAME')) == mapping_name.upper()
            )
            .collect()
        )

        return [row.asDict() for row in rows]


    def _read_mapping_data(
        self,
        definition: MappingDefinition,
        *,
        include_inactive: bool = False,
        include_status: bool = False,
    ) -> DataFrame:
        df = (
            self._store.read('MAPPING_DATA', schema=MAPPING_DATA_SCHEMA)
            .filter(
                F.upper(F.col('MAPPING_NAME')) == definition.mapping_name.upper()
            )
        )

        if not include_inactive:
            df = df.filter(F.upper(F.col('STATUS')) == 'A')

        columns = [
            F.col(field.physical_name).alias(field.logical_name)
            for field in definition.fields
        ]

        if include_status:
            columns.append(F.col('STATUS'))

        return df.select(*columns)


    def _fillna_mapping_columns(
        self,
        data: DataFrame,
        definition: MappingDefinition,
    ) -> DataFrame:
        subset_cols = [
            field.logical_name
            for field in definition.lookup_fields
        ]

        subset_cols.extend([
            field.logical_name
            for field in definition.output_fields
        ])

        subset_cols.extend([
            field.logical_name
            for field in definition.informational_fields
        ])

        return data.fillna('', subset=subset_cols)
