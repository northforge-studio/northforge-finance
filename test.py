from pyspark.sql import SparkSession

from adi.enrichments import TransformationManager
from adi.io import CsvTableStore, TrialBalanceReader
from adi.pipeline import TrialBalancePipeline
from finmap import FinMapClient


spark = (
    SparkSession.builder
    .master('local[*]')
    .appName('trial-balance-pipeline-test')
    .getOrCreate()
)

store = CsvTableStore(spark)
reader = TrialBalanceReader(store)

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

df_source = reader.read().limit(5)

df_staging = pipeline.staging(df_source)

df_staging.show(truncate=False)
df_staging.printSchema()

spark.stop()
