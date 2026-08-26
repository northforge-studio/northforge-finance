from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
)


SEGMENT_DEFAULT_SCHEMA = StructType([
    StructField('SEGMENT_TYPE', StringType(), False),
    StructField('CONTEXT_TYPE', StringType(), False),
    StructField('CONTEXT_VALUE', StringType(), False),
    StructField('DEFAULT_VALUE', StringType(), False),
])
