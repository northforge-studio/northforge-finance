from pyspark.sql import SparkSession

from adi.io import (
    CsvStore,
    TrialBalanceRepository,
    ReferenceRepository,
    TransformationRepository,
)
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
    transformation_manager=transformation_manager,
    reference_manager=reference_manager,
    finmap=finmap,
)

source_df = repository.read_source()

posting_df = pipeline.run(source_df)

posting_df.show()

posting_df.printSchema()

spark.stop()
