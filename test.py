from datetime import date

from pyspark.sql import SparkSession

from adi.repository import (
    TrialBalanceRepository,
    ReferenceRepository,
    TransformationRepository,
)
from core.io.store import CsvStore
from adi.pipeline import TrialBalancePipeline
from adi.config.settings import TABLE_PATHS
from adi.enrichments import (
    TransformationManager,
    ReferenceManager
)
from finmap import FinMapClient


BUSINESS_DT = date(2025, 3, 31)

spark = (
    SparkSession.builder
    .master('local[*]')
    .appName('trial-balance-pipeline-test')
    .getOrCreate()
)

store = CsvStore(spark, table_paths=TABLE_PATHS)
repository = TrialBalanceRepository(store)
reference_repository = ReferenceRepository(store)
transformation_repository = TransformationRepository(store)

transformation_manager = TransformationManager(transformation_repository)
reference_manager = ReferenceManager(reference_repository)

finmap = FinMapClient.from_csv(
    spark=spark,
    metadata_path='data/reference/mapping_meta.csv',
    data_path='data/reference/mapping_data.csv',
)

pipeline = TrialBalancePipeline(
    business_dt=BUSINESS_DT,
    finmap=finmap,
    repository=repository,
    reference_manager=reference_manager,
    transformation_manager=transformation_manager,
)

business_dt, batch_id = pipeline.run()

print(f"Pipeline run complete for business_dt={business_dt}, batch_id={batch_id}")

posting_df = repository.read_posting(business_dt=business_dt, batch_id=batch_id)

posting_df.show()

posting_df.printSchema()

spark.stop()
