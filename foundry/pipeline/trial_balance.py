from datetime import date
from uuid import UUID

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from foundry.pipeline.base import BasePipeline
from foundry.contracts import (
    TRIAL_BALANCE_STAGING_SCHEMA,
    TRIAL_BALANCE_ENRICHMENT_SCHEMA,
    TRIAL_BALANCE_REPORTING_SCHEMA,
    TRIAL_BALANCE_POSTING_SCHEMA,
    TRIAL_BALANCE_INTERFACE_SCHEMA,

)
from foundry.models import PipelineConfig
from foundry.repository import TrialBalanceRepository

from atlas import AtlasClient

from reference import ReferenceClient, ReferenceData
from spec import SpecClient

from core.runs import RunIdentity


class TrialBalancePipeline(BasePipeline):
    DATACLASS = 'TRIAL_BALANCE'


    def __init__(
        self,
        business_dt: date,
        atlas: AtlasClient,
        repository: TrialBalanceRepository,
        reference: ReferenceClient,
        spec: SpecClient,
    ):
        config = PipelineConfig(
            dataclass=self.DATACLASS,
            business_dt=business_dt
        )
        super().__init__(
            config = config,
            atlas = atlas,
            reference = reference,
            spec = spec,
        )
        self._atlas = atlas
        self._repository = repository
        self._reference = reference
        self._spec = spec


    def pre_staging(self) -> DataFrame:
        df = self._repository.read_source(
            business_dt=self._config.business_dt
        )

        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='STG',
            stage='PRE',
        )

        df = self._atlas.apply(df, mapping_name='ENTITY_MAPPING')
        df = self._atlas.apply(df, mapping_name='MEASURE_TYPE_MAPPING')

        df = self._reference.enrich_reference_data(df, ReferenceData.FX_RATE)
        df = self._reference.enrich_reference_data(df, ReferenceData.COUNTERPARTY)

        return df


    def main_staging(self, df: DataFrame) -> DataFrame:
        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='STG',
            stage='MAIN',
        )
        
        return df


    def post_staging(self, df: DataFrame) -> None:
        df = self._add_row_id(df)

        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='STG',
            stage='POST',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_STAGING_SCHEMA)
        df = df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            'SRC_MEASURE_NM',
        )

        self._repository.write_staging(df)


    def pre_enrichment(self, workflow_run_id: UUID) -> DataFrame:
        df = self._repository.read_staging(workflow_run_id)

        gateway_rules = self._atlas.get_rule_config(self.DATACLASS)

        return self._execute_rules(df, gateway_rules)


    def main_enrichment(self, df: DataFrame) -> DataFrame:
        return df


    def post_enrichment(self, df: DataFrame) -> None:
        df = self._add_row_id(df)

        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='ENR',
            stage='POST',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_ENRICHMENT_SCHEMA)
        df = df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
        )

        self._repository.write_enrichment(df)


    def pre_reporting(self, workflow_run_id: UUID) -> DataFrame:
        staging_df = self._repository.read_staging(workflow_run_id)
        enrichment_df = self._repository.read_enrichment(workflow_run_id)

        df = self._combine_staging_and_enrichment(staging_df, enrichment_df)

        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='RPT',
            stage='PRE',
        )

        return df


    def main_reporting(self, df: DataFrame) -> DataFrame:
        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='RPT',
            stage='MAIN',
        )

        return df


    def post_reporting(self, df: DataFrame) -> None:
        df = self._add_row_id(df)

        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='RPT',
            stage='POST',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_REPORTING_SCHEMA)
        df = df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            'SRC_MEASURE_NM',
        )

        self._repository.write_reporting(df)


    def pre_posting(self, workflow_run_id: UUID) -> DataFrame:
        df = self._repository.read_reporting(workflow_run_id)

        df = self._transpose_measures(df)

        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='PST',
            stage='PRE',
        )

        return df


    def main_posting(self, df: DataFrame) -> DataFrame:
        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='PST',
            stage='MAIN',
        )

        return df


    def post_posting(self, df: DataFrame) -> None:
        df = self._add_row_id(df)

        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='PST',
            stage='POST',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_POSTING_SCHEMA)
        df = df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            self._numeric_id('POSTING_ID'),
        )

        self._repository.write_posting(df)


    def pre_interface(self, workflow_run_id: UUID) -> DataFrame:
        df = self._repository.read_posting(workflow_run_id)

        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='INT',
            stage='PRE',
        )

        return df


    def main_interface(self, df: DataFrame) -> DataFrame:
        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='INT',
            stage='MAIN',
        )
        
        df = self._spec.apply_file_layout(
            df,
            dataclass=self.DATACLASS,
        )

        return df


    def post_interface(self, df: DataFrame) -> None:
        df = self._spec.apply_transformation(
            df,
            dataclass=self.DATACLASS,
            zone='INT',
            stage='POST',
        )

        df = self._align_to_schema(df, TRIAL_BALANCE_INTERFACE_SCHEMA)
        df = df.orderBy(
            self._numeric_id('SRC_RECORD_ID'),
            self._numeric_id('LINE_NUMBER'),
        )

        self._repository.write_interface(df)
    

    def rollback_execution(self, operation: str, identity: RunIdentity) -> None:
        handlers = {
            'STAGING': self._repository.delete_staging,
            'ENRICHMENT': self._repository.delete_enrichment,
            'REPORTING': self._repository.delete_reporting,
            'POSTING': self._repository.delete_posting,
            'INTERFACE': self._repository.delete_interface,
        }

        handler = handlers.get(operation)
        if handler is not None:
            handler(identity.workflow_run_id)


    def _combine_staging_and_enrichment(
        self,
        staging_df: DataFrame,
        enrichment_df: DataFrame,
    ) -> DataFrame:
        enrichment_only_columns = [
            field.name
            for field in TRIAL_BALANCE_ENRICHMENT_SCHEMA.fields
            if field.name not in {f.name for f in TRIAL_BALANCE_STAGING_SCHEMA.fields}
        ]

        row_identity_columns = ['SRC_RECORD_ID', 'SRC_MEASURE_NM']

        unprocessed_staging_df = staging_df.join(
            enrichment_df.select(*row_identity_columns),
            on=row_identity_columns,
            how='left_anti',
        )

        for column in enrichment_only_columns:
            unprocessed_staging_df = unprocessed_staging_df.withColumn(
                column, F.lit('')
            )

        return enrichment_df.unionByName(unprocessed_staging_df)


    def _transpose_measures(self, df: DataFrame) -> DataFrame:
        group_by_columns = ['SRC_RECORD_ID']

        posting_measure_names = [
            'PREVIOUS_DAY_BALANCE',
            'CURRENT_DAY_DEBIT_BALANCE',
            'CURRENT_DAY_CREDIT_BALANCE',
            'CURRENT_DAY_EOD_BALANCE',
            'BACK_VALUE_ADJUSTED_BALANCE',
            'ADJUSTED_BALANCE',
        ]

        value_columns = [
            'SRC_MEASURE_TRANS_AMT',
            'POSTING_MEASURE_TRANS_AMT',
        ]

        postable_df = df.filter(
            F.col('MEASURE_TYPE') == 'POSTABLE'
        )

        pivoted_df = (
            df
            .groupBy(*group_by_columns)
            .pivot(
                'POSTING_MEASURE_NM',
                posting_measure_names,
            )
            .agg(
                *[
                    F.first(column).alias(column)
                    for column in value_columns
                ]
            )
        )

        output_measure_columns = []

        select_expr = [
            F.col(column)
            for column in group_by_columns
        ]

        for measure_name in posting_measure_names:
            source_output = measure_name
            posting_output = f'POSTING_{measure_name}'

            select_expr.extend([
                F.col(
                    f'{measure_name}_SRC_MEASURE_TRANS_AMT'
                ).alias(source_output),

                F.col(
                    f'{measure_name}_POSTING_MEASURE_TRANS_AMT'
                ).alias(posting_output),
            ])

            output_measure_columns.extend([
                source_output,
                posting_output,
            ])

        pivoted_df = pivoted_df.select(*select_expr)

        return (
            postable_df
            .join(
                pivoted_df,
                on=group_by_columns,
                how='inner',
            )
            .select(
                *postable_df.columns,
                *output_measure_columns,
            )
        )
