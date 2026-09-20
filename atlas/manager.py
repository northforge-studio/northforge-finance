from functools import reduce

from pyspark.sql import functions as F
from pyspark.sql import Column, DataFrame, Window

from atlas.repository import AtlasRepository
from atlas.models import (
    Mapping,
    MappingCandidateEvidence,
    MappingCandidateType,
    MappingResolutionEvidence,
    PostingRule,
    GatewayRule
)


class MappingManager:
    _ROW_ID = '__mapping_row_id'


    def __init__(self, repository: AtlasRepository):
        self._repository = repository


    def get_mapping(self, mapping_name: str) -> Mapping:
        return self._repository.get_mapping(mapping_name)


    def apply(
        self,
        df: DataFrame,
        mapping_name: str,
    ) -> DataFrame:
        mapping = self.get_mapping(mapping_name)

        df = self._validate(df, mapping)

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

        # weightage based resolution
        resolved_df = self._resolve_candidates(
            candidate_df=candidate_df,
            source_alias=source_alias,
            mapping_alias=mapping_alias,
        )

        result_df = self._select_result_columns(
            joined_df=resolved_df,
            source_alias=source_alias,
            mapping_alias=mapping_alias,
            source_columns=source_columns,
            mapping=mapping,
        )

        if mapping.definition.attr_reference_fields:
            result_df = self._resolve_attribute_references(
                result_df,
                mapping,
            )

        return result_df


    def get_rule_config(
        self,
        dataclass: str,
    ) -> list[GatewayRule]:
        mapping = self.get_mapping('POSTING_RULES_MAPPING')

        rows = (
            mapping.data
            .filter(
                (F.upper(F.col('DATACLASS')) == F.upper(F.lit(dataclass)))
                | (F.col('DATACLASS') == '*')
            )
            .select('POSTING_RULE_ID', 'GATEWAY_RULE_ID', 'POSTING_STREAM', 'POSTING_MEASURE_NM')
            .collect()
        )

        rule_cfg: dict[str, dict[str, object]] = {}

        for row in rows:
            gateway_cfg = rule_cfg.setdefault(
                row['GATEWAY_RULE_ID'],
                {
                    'POSTING_MEASURE_NM': row['POSTING_MEASURE_NM'],
                    'POSTING_RULES': [],
                },
            )

            gateway_cfg['POSTING_RULES'].append(
                PostingRule(
                    id=row['POSTING_RULE_ID'],
                    posting_stream=row['POSTING_STREAM'],
                )
            )

        return [
            GatewayRule(
                id=gateway_rule_id,
                posting_measure_nm=gateway_cfg['POSTING_MEASURE_NM'],
                posting_rules=tuple(gateway_cfg['POSTING_RULES']),
            )
            for gateway_rule_id, gateway_cfg
            in rule_cfg.items()
        ]


    def explain_resolution(
        self,
        mapping_name: str,
        input_values: dict[str, str],
    ) -> MappingResolutionEvidence:
        mapping = self._repository.get_mapping_details(mapping_name)

        self._validate_input_values(mapping, input_values)

        source_alias = 'source'
        mapping_alias = 'mapping'

        source_df = self._build_diagnostic_source_row(
            mapping=mapping,
            input_values=input_values,
        ).alias(source_alias)

        mapping_df = mapping.data.alias(mapping_alias)

        join_condition = self._build_join_condition(
            source_alias=source_alias,
            mapping_alias=mapping_alias,
            mapping=mapping,
        )

        candidate_df = source_df.join(
            mapping_df,
            on=join_condition,
            how='inner',
        )

        candidates = self._collect_candidate_evidence(
            candidate_df=candidate_df,
            mapping_alias=mapping_alias,
            mapping=mapping,
        )

        active_candidate_df = candidate_df.filter(
            F.upper(F.col(f'{mapping_alias}.STATUS')) == 'A'
        )

        # Reuses the same weightage-ranking/tie logic apply() uses, so a
        # tie among active candidates raises the same ValueError here.
        resolved_df = self._resolve_candidates(
            candidate_df=active_candidate_df,
            source_alias=source_alias,
            mapping_alias=mapping_alias,
        )

        resolved_rows = resolved_df.select(
            *[
                F.col(f'{mapping_alias}.{field.logical_name}').alias(field.logical_name)
                for field in mapping.definition.output_fields
            ]
        ).collect()

        resolved_output = (
            {
                field.logical_name: resolved_rows[0][field.logical_name]
                for field in mapping.definition.output_fields
            }
            if resolved_rows
            else None
        )

        return MappingResolutionEvidence(
            mapping_name=mapping.definition.mapping_name,
            input_values=dict(input_values),
            candidates=candidates,
            active_candidate_found=any(
                candidate.status.upper() == 'A'
                for candidate in candidates
            ),
            resolved=bool(resolved_rows),
            mapping_output=resolved_output,
        )


    def _validate_input_values(
        self,
        mapping: Mapping,
        input_values: dict[str, str],
    ) -> None:
        required_columns = {
            field.src_field_name
            for field in mapping.definition.lookup_fields
            if field.src_field_name is not None
        }

        missing_columns = required_columns - set(input_values)

        if missing_columns:
            raise ValueError(
                f'Mapping {mapping.definition.mapping_name!r} '
                f'requires source columns {sorted(missing_columns)}'
            )


    def _build_diagnostic_source_row(
        self,
        mapping: Mapping,
        input_values: dict[str, str],
    ) -> DataFrame:
        source_columns = [
            field.src_field_name
            for field in mapping.definition.lookup_fields
        ]

        spark = mapping.data.sparkSession

        return (
            spark
            .createDataFrame(
                [tuple(input_values[column] for column in source_columns)],
                schema=source_columns,
            )
            .withColumn(self._ROW_ID, F.monotonically_increasing_id())
        )


    def _collect_candidate_evidence(
        self,
        candidate_df: DataFrame,
        mapping_alias: str,
        mapping: Mapping,
    ) -> tuple[MappingCandidateEvidence, ...]:
        lookup_fields = mapping.definition.lookup_fields
        output_fields = mapping.definition.output_fields

        selected_df = candidate_df.select(
            F.col(f'{mapping_alias}.STATUS').alias('STATUS'),
            F.col(f'{mapping_alias}.WEIGHTAGE').alias('WEIGHTAGE'),
            *[
                F.col(f'{mapping_alias}.{field.logical_name}').alias(field.logical_name)
                for field in lookup_fields
            ],
            *[
                F.col(f'{mapping_alias}.{field.logical_name}').alias(field.logical_name)
                for field in output_fields
            ],
        )

        candidates = []

        for row in selected_df.collect():
            wildcard_fields = tuple(
                field.logical_name
                for field in lookup_fields
                if row[field.logical_name] == '*'
            )

            candidates.append(
                MappingCandidateEvidence(
                    status=row['STATUS'],
                    weightage=row['WEIGHTAGE'],
                    candidate_type=(
                        MappingCandidateType.WILDCARD
                        if wildcard_fields
                        else MappingCandidateType.SPECIFIC
                    ),
                    wildcard_fields=wildcard_fields,
                    lookup_values={
                        field.logical_name: row[field.logical_name]
                        for field in lookup_fields
                    },
                    output_values={
                        field.logical_name: row[field.logical_name]
                        for field in output_fields
                    },
                )
            )

        return tuple(candidates)


    def _validate(
        self,
        df: DataFrame,
        mapping: Mapping,
    ) -> DataFrame:
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
            df = df.drop(*conflicting_columns)

        return df


    def _build_join_condition(
        self,
        source_alias: str,
        mapping_alias: str,
        mapping: Mapping,
    ) -> Column:
        conditions = [
            (
                F.upper(F.col(
                    f'{mapping_alias}.{field.logical_name}'
                ))
                == F.upper(F.coalesce(
                    F.col(f'{source_alias}.{field.src_field_name}').cast('string'),
                    F.lit('')
                ))
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


    def _get_attribute_references(self) -> dict[str, str]:
        df = self.get_mapping('ATTR_REFERENCE_MAPPING').data

        return {
            row['ATTR_REFERENCE_NAME']: row['ATTR_REFERENCE_VALUE']
            for row in df.select(
                'ATTR_REFERENCE_NAME',
                'ATTR_REFERENCE_VALUE',
            ).collect()
        }


    def _resolve_attribute_references(
        self,
        df: DataFrame,
        mapping: Mapping,
    ) -> DataFrame:
        references = self._get_attribute_references()

        for field in mapping.definition.attr_reference_fields:
            column_name = field.logical_name
            original_value = F.col(column_name)

            resolved_value = original_value

            for reference_name, reference_value in references.items():
                resolved_value = (
                    F.when(
                        original_value == reference_name,
                        F.col(reference_value),
                    )
                    .otherwise(resolved_value)
                )

            df = df.withColumn(
                column_name,
                resolved_value,
            )

        return df
