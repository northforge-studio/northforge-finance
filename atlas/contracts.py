from pyspark.sql.types import (
    IntegerType,
    StringType,
    StructField,
    StructType,
)


MAPPING_META_SCHEMA = StructType([
    StructField('MAPPING_NAME', StringType(), True),
    StructField('MAPPING_DATA_NAME', StringType(), True),
    StructField('METADATA_FIELD_NAME', StringType(), True),
    StructField('LOGICAL_FIELD_NAME', StringType(), True),
    StructField('FIELD_TYPE', StringType(), True),
    StructField('LOOKUP_TYPE', StringType(), True),
    StructField('SRC_FIELD_NAME', StringType(), True),
    StructField('DATATYPE', StringType(), True),
    StructField('UI_FIELD_ORDER', IntegerType(), True),
])


MAPPING_DATA_SCHEMA = StructType([
    StructField('MAPPING_NAME', StringType(), True),

    *[
        StructField(
            f'INPUT_COL{i}',
            StringType(),
            True,
        )
        for i in range(1, 21)
    ],

    *[
        StructField(
            f'OUTPUT_COL{i}',
            StringType(),
            True,
        )
        for i in range(1, 21)
    ],

    StructField('WEIGHTAGE', StringType(), True),
])
