from functools import reduce

from pyspark.sql import functions as F
from pyspark.sql import Column, DataFrame, Window

from finmap.models import Mapping
from finmap.repository import MappingRepository


class MappingManager:
    _ROW_ID = '__mapping_row_id'


    def __init__(self, repository: MappingRepository):
        self._repository = repository


    def get_mapping(self, mapping_name: str) -> Mapping:
        return self._repository.get_mapping(mapping_name)


    def validate(
        self,
        df: DataFrame,
        mapping: Mapping,
    ) -> None:
        required_columns = {
            field.src_field_name
            for field in mapping.definition.lookup_fields
            if field.src_field_name is not None
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f'Mapping {mapping.definition.mapping_name!r} '
                f'requires source columns {sorted(missing_columns)}'
            )

        output_columns = {
            field.logical_name
            for field in mapping.definition.output_fields
        }

        conflicting_columns = output_columns & set(df.columns)

        if conflicting_columns:
            raise ValueError(
                f'Mapping {mapping.definition.mapping_name!r} '
                f'output columns already exist in source '
                f'{sorted(conflicting_columns)}'
            )


    def apply(
        self,
        df: DataFrame,
        mapping_name: str,
    ) -> DataFrame:
        mapping = self.get_mapping(mapping_name)

        self.validate(
            df,
            mapping,
        )

        source_alias = 'source'
        mapping_alias = 'mapping'

        source_columns = df.columns

        source_df = (
            df
            .withColumn(
                self._ROW_ID,
                F.monotonically_increasing_id(),
            )
            .alias(source_alias)
        )

        mapping_df = mapping.data.alias(mapping_alias)

        join_condition = self._build_join_condition(
            source_alias=source_alias,
            mapping_alias=mapping_alias,
            mapping=mapping,
        )

        candidate_df = source_df.join(
            mapping_df,
            on=join_condition,
            how='left',
        )

        resolved_df = self._resolve_candidates(
            candidate_df=candidate_df,
            source_alias=source_alias,
            mapping_alias=mapping_alias,
        )

        return self._select_result_columns(
            joined_df=resolved_df,
            source_alias=source_alias,
            mapping_alias=mapping_alias,
            source_columns=source_columns,
            mapping=mapping,
        )


    def _build_join_condition(
        self,
        source_alias: str,
        mapping_alias: str,
        mapping: Mapping,
    ) -> Column:
        conditions = [
            (
                F.col(
                    f'{mapping_alias}.{field.logical_name}'
                )
                == F.col(
                    f'{source_alias}.{field.src_field_name}'
                )
            )
            |
            (
                F.col(
                    f'{mapping_alias}.{field.logical_name}'
                )
                == F.lit('*')
            )
            for field in mapping.definition.lookup_fields
        ]

        return reduce(
            lambda x, y: x & y,
            conditions
        )


    def _resolve_candidates(
        self,
        candidate_df: DataFrame,
        source_alias: str,
        mapping_alias: str,
    ) -> DataFrame:
        row_id = F.col(
            f'{source_alias}.{self._ROW_ID}'
        )

        weightage = F.col(
            f'{mapping_alias}.WEIGHTAGE'
        ).cast('string')

        window = Window.partitionBy(row_id)

        ranked_df = candidate_df.withColumn(
            '__max_weightage',
            F.max(weightage).over(window),
        )

        has_tie = (
            ranked_df
            .filter(
                weightage == F.col('__max_weightage')
            )
            .groupBy(row_id)
            .count()
            .filter(F.col('count') > 1)
            .limit(1)
            .count()
            > 0
        )

        if has_tie:
            raise ValueError(
                'Multiple mapping candidates have the same '
                'highest WEIGHTAGE'
            )

        rank_window = (
            Window
            .partitionBy(row_id)
            .orderBy(
                weightage.desc_nulls_last()
            )
        )

        return (
            ranked_df
            .withColumn(
                '__mapping_rank',
                F.row_number().over(rank_window),
            )
            .filter(
                F.col('__mapping_rank') == 1
            )
            .drop(
                '__mapping_rank',
                '__max_weightage',
            )
        )


    def _select_result_columns(
        self,
        joined_df: DataFrame,
        source_alias: str,
        mapping_alias: str,
        source_columns: list[str],
        mapping: Mapping,
    ) -> DataFrame:
        source_columns = [
            F.col(f'{source_alias}.{column}')
            for column in source_columns
        ]

        output_columns = [
            F.col(
                f'{mapping_alias}.{field.logical_name}'
            ).alias(field.logical_name)
            for field in mapping.definition.output_fields
        ]

        return joined_df.select(
            *source_columns,
            *output_columns,
        )
