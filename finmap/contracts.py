from pyspark.sql.types import (
    DateType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)


MAPPING_META_SCHEMA = StructType([
    StructField('AUD_LOAD_ID', StringType(), True),
    StructField('RCD_DT', DateType(), True),
    StructField('VER_NB', IntegerType(), True),
    StructField('EFF_START_DATE', DateType(), True),
    StructField('EFF_END_DATE', DateType(), True),
    StructField('MAPPING_CATEGORY', StringType(), True),
    StructField('MAPPING_NAME', StringType(), True),
    StructField('MAPPING_DATA_NAME', StringType(), True),
    StructField('METADATA_FIELD_NAME', StringType(), True),
    StructField('LOGICAL_FIELD_NAME', StringType(), True),
    StructField('FIELD_TYPE', StringType(), True),
    StructField('LOOKUP_TYPE', StringType(), True),
    StructField('DATATYPE', StringType(), True),
    StructField('SRC_FIELD_NAME', StringType(), True),
    StructField('UI_FIELD_VISIBILITY', StringType(), True),
    StructField('CONTROL', StringType(), True),
    StructField('UI_FIELD_ORDER', IntegerType(), True),
])


MAPPING_DATA_SCHEMA = StructType([
    StructField('AUD_LOAD_ID', StringType(), True),
    StructField('RCD_DT', DateType(), True),
    StructField('VER_NB', IntegerType(), True),
    StructField('EFF_START_DATE', DateType(), True),
    StructField('EFF_END_DATE', DateType(), True),
    StructField('MDM_ID', StringType(), True),
    StructField('MAPPING_CATEGORY', StringType(), True),
    StructField('MAPPING_NAME', StringType(), True),
    StructField('MAPPING_DATA_NAME', StringType(), True),

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
