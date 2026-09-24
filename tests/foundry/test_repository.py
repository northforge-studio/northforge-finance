from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pyspark.sql.types import DateType, DecimalType

from core.store import CsvStore
from foundry.contracts import (
    TRIAL_BALANCE_STAGING_SCHEMA,
    TRIAL_BALANCE_ENRICHMENT_SCHEMA,
)
from foundry.repository import TrialBalanceRepository

from tests.support.constants import BUSINESS_DT


def _default_for(field) -> date | Decimal | str:
    if isinstance(field.dataType, DateType):
        return BUSINESS_DT
    if isinstance(field.dataType, DecimalType):
        return Decimal('0')
    return ''


def _build_row(schema, **overrides) -> tuple:
    values = {field.name: _default_for(field) for field in schema.fields}
    values.update(overrides)
    return tuple(values[field.name] for field in schema.fields)


@pytest.fixture
def repository(spark, tmp_path):
    store = CsvStore(
        spark=spark,
        table_locations={
            'TRIAL_BALANCE_STAGING': tmp_path / 'STAGING',
            'TRIAL_BALANCE_ENRICHMENT': tmp_path / 'ENRICHMENT',
        },
    )
    return TrialBalanceRepository(store)


def _write_staging_row(repository, spark, **overrides) -> None:
    row = _build_row(TRIAL_BALANCE_STAGING_SCHEMA, BUSINESS_DT=BUSINESS_DT, **overrides)
    df = spark.createDataFrame([row], schema=TRIAL_BALANCE_STAGING_SCHEMA)
    repository.write_staging(df)


def _write_enrichment_row(repository, spark, **overrides) -> None:
    row = _build_row(TRIAL_BALANCE_ENRICHMENT_SCHEMA, BUSINESS_DT=BUSINESS_DT, **overrides)
    df = spark.createDataFrame([row], schema=TRIAL_BALANCE_ENRICHMENT_SCHEMA)
    repository.write_enrichment(df)


def test_read_staging_returns_only_the_named_workflows_rows(repository, spark):
    kept = str(uuid4())
    other = str(uuid4())

    _write_staging_row(repository, spark, WORKFLOW_RUN_ID=kept, SRC_RECORD_ID='rec-1')
    _write_staging_row(repository, spark, WORKFLOW_RUN_ID=other, SRC_RECORD_ID='rec-2')

    df = repository.read_staging(kept)

    rows = df.collect()
    assert len(rows) == 1
    assert rows[0]['WORKFLOW_RUN_ID'] == kept
    assert rows[0]['SRC_RECORD_ID'] == 'rec-1'


def test_read_staging_preserves_producer_run_id_on_returned_rows(repository, spark):
    # PRODUCER_RUN_ID is retained as exact producer lineage even though
    # WORKFLOW_RUN_ID is now the operational read key.
    workflow_run_id = str(uuid4())
    producer_run_id = str(uuid4())

    _write_staging_row(
        repository, spark,
        WORKFLOW_RUN_ID=workflow_run_id,
        PRODUCER_RUN_ID=producer_run_id,
        SRC_RECORD_ID='rec-1',
    )

    row = repository.read_staging(workflow_run_id).collect()[0]

    assert row['PRODUCER_RUN_ID'] == producer_run_id


def test_read_staging_raises_when_no_rows_for_workflow(repository):
    with pytest.raises(ValueError, match='No staging data found'):
        repository.read_staging(uuid4())


def test_read_enrichment_returns_only_the_named_workflows_rows(repository, spark):
    kept = str(uuid4())
    other = str(uuid4())

    _write_enrichment_row(repository, spark, WORKFLOW_RUN_ID=kept, SRC_RECORD_ID='rec-1')
    _write_enrichment_row(repository, spark, WORKFLOW_RUN_ID=other, SRC_RECORD_ID='rec-2')

    df = repository.read_enrichment(kept)

    rows = df.collect()
    assert len(rows) == 1
    assert rows[0]['WORKFLOW_RUN_ID'] == kept
    assert rows[0]['SRC_RECORD_ID'] == 'rec-1'


def test_repository_has_no_batch_id_generation_method(repository):
    assert not hasattr(repository, 'get_next_batch_id')
