from pyspark.sql import SparkSession

from adi.enrichments import TransformationManager
from adi.io import CsvTableStore, TrialBalanceReader

from finmap import CsvMappingRepository


spark = (
    SparkSession.builder
    .master('local[*]')
    .appName('trial-balance-source-read-test')
    .getOrCreate()
)

store = CsvTableStore(spark)
reader = TrialBalanceReader(store)

df_tb_src = reader.read().limit(5)

transformation_manager = TransformationManager(spark)

df_tb_pre_stage = transformation_manager.apply(
    df = df_tb_src,
    dataclass= 'TRIAL_BALANCE',
    zone= 'staging',
    stage= 'pre'
)

df_tb_pre_stage.show()

finmap = CsvMappingRepository(
    spark=spark,
    metadata_path='data/reference/mapping_meta.csv',
    data_path='data/reference/mapping_data.csv',
)

finmap.get_mapping('ENTITY_MAPPING').data.show(n=5, truncate=True)

spark.stop()
