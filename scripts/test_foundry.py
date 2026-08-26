from datetime import date

from pyspark.sql import SparkSession

from foundry.repository import TrialBalanceRepository
from foundry.pipeline import TrialBalancePipeline
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
from spec import SpecClient


BUSINESS_DT = date(2026, 3, 31)

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

store = PostgresStore(
    spark, 
    table_names = POSTGRES_TABLE_LOCATIONS
)

repository = TrialBalanceRepository(store)

spec = SpecClient.from_db(
    spark=spark,
    transformation_table='spec.transformation',
    file_layout_table='spec.file_layout',
)

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
    spec=spec,
    run_tracker=run_tracker,
)

pipeline_result = pipeline.execute()

print(f"Pipeline run complete: {pipeline_result}")

business_dt = pipeline._config.business_dt
batch_id = pipeline._config.batch_id

posting_df = repository.read_staging(business_dt=business_dt, batch_id=batch_id)

posting_df.show()

posting_df.printSchema()

spark.stop()
