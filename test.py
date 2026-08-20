from pyspark.sql import SparkSession

from adi.enrichments import TransformationManager
from adi.io import CsvStore, TrialBalanceRepository
from adi.pipeline import TrialBalancePipeline
from adi.config.settings import TABLE_PATHS

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

finmap = FinMapClient.from_csv(
    spark=spark,
    metadata_path='data/reference/mapping_meta.csv',
    data_path='data/reference/mapping_data.csv',
)

pipeline = TrialBalancePipeline(
    transformation_manager=transformation_manager,
    finmap=finmap,
)

df_source = repository.read_source().limit(5)

df_staging = pipeline.staging(df_source)

df_staging.show(truncate=False)
df_staging.printSchema()

spark.stop()
