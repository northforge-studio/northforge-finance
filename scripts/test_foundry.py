from datetime import date

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
from core.db import PostgresConfig

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
    config = PostgresConfig.from_env(),
    table_locations = POSTGRES_TABLE_LOCATIONS
)

repository = TrialBalanceRepository(csv_store)

transformation_repository = TransformationRepository(postgres_store)
transformation_manager = TransformationManager(transformation_repository)

reference = ReferenceClient.from_csv(
    spark=spark,
    fx_rate_path='data/reference/fx_rate.csv',
    counterparty_path='data/reference/counterparty.csv',
)

atlas = AtlasClient.from_csv(
    spark=spark,
    metadata_path='data/atlas/mapping_meta.csv',
    data_path='data/atlas/mapping_data.csv',
)

pipeline = TrialBalancePipeline(
    business_dt=BUSINESS_DT,
    atlas=atlas,
    repository=repository,
    reference=reference,
    transformation_manager=transformation_manager,
)

business_dt, batch_id = pipeline.run()

print(f"Pipeline run complete for business_dt={business_dt}, batch_id={batch_id}")

posting_df = repository.read_posting(business_dt=business_dt, batch_id=batch_id)

posting_df.show()

posting_df.printSchema()

spark.stop()
