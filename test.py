from pyspark.sql import SparkSession

from adi.io import CsvTableStore, TrialBalanceReader


spark = (
    SparkSession.builder
    .master('local[*]')
    .appName('trial-balance-source-read-test')
    .getOrCreate()
)

store = CsvTableStore(spark)
reader = TrialBalanceReader(store)

df = reader.read()

df.show(10, truncate=False)
df.printSchema()

print(f'Row count: {df.count()}')

spark.stop()
