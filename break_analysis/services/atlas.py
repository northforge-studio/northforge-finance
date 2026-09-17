from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from core.logging import get_logger, short_id

from atlas import AtlasClient
from atlas.models import MappingDefinition

from foundry.contracts import TRIAL_BALANCE_POSTING_SEGMENT_COLUMNS
from foundry.repository import TrialBalanceRepository

from break_analysis.models import AtlasInputValues, BreakRecord


logger = get_logger(__name__)


_AS_OF_DATE_COLUMN = 'AS_OF_DT'
_ACCOUNTED_CURRENCY_COLUMN = 'POSTING_MEASURE_FUNC_CCY_CD'


class AtlasEvidenceService:
    def __init__(
        self,
        atlas_client: AtlasClient,
        foundry_repository: TrialBalanceRepository,
    ):
        self._atlas = atlas_client
        self._foundry = foundry_repository


    def get_mapping_input_values(
        self,
        break_record: BreakRecord,
        mapping_name: str,
    ) -> tuple[AtlasInputValues, ...]:
        case_id = short_id(break_record.recon_result_id)

        definition = self._atlas.get_definition(mapping_name)
        input_columns = self._input_columns(definition)

        postings_df = self._foundry.read_posting(break_record.workflow_run_id)

        missing_columns = set(input_columns) - set(postings_df.columns)
        if missing_columns:
            raise ValueError(
                f'Mapping {mapping_name!r} requires foundry_posting columns '
                f'{sorted(missing_columns)} that are not present in '
                f'foundry_posting.'
            )

        matched_df = self._match_break_record(postings_df, break_record)

        if matched_df.isEmpty():
            raise ValueError(
                f'No foundry_posting rows found for recon_result_id='
                f'{break_record.recon_result_id} in workflow_run_id='
                f'{break_record.workflow_run_id}.'
            )

        grouped_rows = (
            matched_df
            .select(*input_columns)
            .groupBy(*input_columns)
            .count()
            .collect()
        )

        logger.info(
            'Atlas mapping input values retrieved | recon_result_id=%s | '
            'mapping_name=%s | input_columns=%s | distinct_combinations=%s',
            case_id, mapping_name, input_columns, len(grouped_rows),
        )

        return tuple(
            AtlasInputValues(
                values={column: row[column] for column in input_columns},
                source_record_count=row['count'],
            )
            for row in grouped_rows
        )


    def _input_columns(
        self,
        definition: MappingDefinition,
    ) -> tuple[str, ...]:
        if not definition.input_fields:
            raise ValueError(
                f'Mapping {definition.mapping_name!r} has no input fields.'
            )

        missing_src_field_names = [
            field.logical_name
            for field in definition.input_fields
            if field.src_field_name is None
        ]

        if missing_src_field_names:
            raise ValueError(
                f'Mapping {definition.mapping_name!r} has input fields '
                f'without a src_field_name: {sorted(missing_src_field_names)}.'
            )

        return tuple(
            field.src_field_name
            for field in definition.input_fields
        )


    def _match_break_record(
        self,
        postings_df: DataFrame,
        break_record: BreakRecord,
    ) -> DataFrame:
        conditions = [
            F.col(_AS_OF_DATE_COLUMN) == break_record.as_of_date,
            F.col(_ACCOUNTED_CURRENCY_COLUMN) == break_record.accounted_currency,
        ]

        for segment_type, column in TRIAL_BALANCE_POSTING_SEGMENT_COLUMNS.items():
            segment_value = getattr(
                break_record.segments,
                segment_type.field_name,
            )

            # Foundry stores an unresolved/blank segment as '', not NULL.
            conditions.append(
                F.col(column) == (segment_value or '')
            )

        return postings_df.filter(reduce(lambda a, b: a & b, conditions))
