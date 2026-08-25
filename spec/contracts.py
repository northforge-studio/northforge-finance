from pyspark.sql.types import (
    IntegerType,
    StringType,
    StructField,
    StructType,
)


TRANSFORMATION_SCHEMA = StructType([
    StructField('SRC_APP_CD', StringType(), False),
    StructField('DATACLASS', StringType(), False),
    StructField('OUTPUT_COL_NAME', StringType(), False),
    StructField('SEQ', IntegerType(), False),
    StructField('ZONE', StringType(), False),
    StructField('STAGE', StringType(), False),
    StructField('SUB_STAGE', StringType(), True),
    StructField('EXPRESSION', StringType(), False),
    StructField('STATUS', StringType(), False),
])


FILE_LAYOUT_SCHEMA = StructType([
    StructField('SRC_APP_CD', StringType(), False),
    StructField('DATACLASS', StringType(), False),
    StructField('POSTING_ATTRIBUTE_NAME', StringType(), False),
    StructField('GL_ATTRIBUTE_NAME', StringType(), False),
    StructField('EXPRESSION', StringType(), False),
    StructField('SEQ', IntegerType(), False),
])
