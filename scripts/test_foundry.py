from datetime import date
from uuid import uuid4

from pyspark.sql import SparkSession

from foundry.repository import (
    TrialBalanceRepository,
    TransformationRepository,
)
from foundry.pipeline import TrialBalancePipeline
from foundry.enrichments import TransformationManager
from foundry.config.settings import (
    CSV_TABLE_LOCATIONS,
    POSTGRES_TABLE_LOCATIONS,
)

from core.store import (
    CsvStore,
    PostgresStore,
)
from core.runs import RunRepository, RunTracker

from atlas import AtlasClient
from reference import ReferenceClient


BUSINESS_DT = date(2025, 3, 31)

spark = (
    SparkSession.builder
    .master('local[*]')
    .appName('foundry-dev')
    .config(
        'spark.jars.packages',
        'org.postgresql:postgresql:42.7.7',
    )
    .getOrCreate()
)

csv_store = CsvStore(spark, table_locations=CSV_TABLE_LOCATIONS)

postgres_store = PostgresStore(
    spark, 
    table_names = POSTGRES_TABLE_LOCATIONS
)

repository = TrialBalanceRepository(csv_store)

transformation_repository = TransformationRepository(postgres_store)
transformation_manager = TransformationManager(transformation_repository)

reference = ReferenceClient.from_db(
    spark = spark,
    fx_rate_table='reference.fx_rate',
    counterparty_table='reference.counterparty',
)

atlas = AtlasClient.from_csv(
    spark=spark,
    metadata_path='data/atlas/mapping_meta.csv',
    data_path='data/atlas/mapping_data.csv',
)

run_tracker = RunTracker(RunRepository())

pipeline = TrialBalancePipeline(
    business_dt=BUSINESS_DT,
    atlas=atlas,
    repository=repository,
    reference=reference,
    transformation_manager=transformation_manager,
    run_tracker=run_tracker,
)

workflow_run_id = uuid4()

pipeline_result = pipeline.run(workflow_run_id=workflow_run_id)

print(f"Pipeline run complete: {pipeline_result}")

business_dt = pipeline._config.business_dt
batch_id = pipeline._config.batch_id

staging_df = repository.read_staging(business_dt=business_dt, batch_id=batch_id)

staging_df.show()

staging_df.printSchema()

spark.stop()
