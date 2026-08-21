from pyspark.sql import SparkSession

from adi.io import CsvStore, TrialBalanceRepository
from adi.pipeline import TrialBalancePipeline
from adi.config.settings import TABLE_PATHS
from adi.enrichments import (
    TransformationManager, 
    ReferenceManager
)

from finmap import FinMapClient


spark = (
    SparkSession.builder
    .master('local[*]')
    .appName('trial-balance-pipeline-test')
    .getOrCreate()
)

store = CsvStore(spark, table_paths=TABLE_PATHS)
repository = TrialBalanceRepository(store)

transformation_manager = TransformationManager(spark)
reference_manager = ReferenceManager(spark)

finmap = FinMapClient.from_csv(
    spark=spark,
    metadata_path='data/reference/mapping_meta.csv',
    data_path='data/reference/mapping_data.csv',
)

pipeline = TrialBalancePipeline(
    transformation_manager=transformation_manager,
    reference_manager=reference_manager,
    finmap=finmap,
)

df_source = repository.read_source()

df_staging = pipeline.staging(df_source)

repository.write_staging(df_staging)

df_staging_reloaded = repository.read_staging()

df_staging_reloaded.show(truncate=False)
df_staging_reloaded.printSchema()

spark.stop()
