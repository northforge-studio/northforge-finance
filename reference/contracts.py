from pyspark.sql.types import (
    DateType,
    DecimalType,
    StringType,
    StructField,
    StructType,
)


FX_RATE_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('CONVERSION_DT', DateType(), True),
        StructField('VER_NB', StringType(), True),
        StructField('FROM_CURRENCY', StringType(), True),
        StructField('TO_CURRENCY', StringType(), True),
        StructField('FX_RATE', DecimalType(28, 12), True),
    ]
)


COUNTERPARTY_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', StringType(), True),
        StructField('CPTY_REF_ID', StringType(), True),
        StructField('CLIENT_ID', StringType(), True),
        StructField('CPTY_NM', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
    ]
)
