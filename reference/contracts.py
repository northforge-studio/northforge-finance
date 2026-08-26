from pyspark.sql.types import (
    DateType,
    DecimalType,
    StringType,
    StructField,
    StructType,
)


FX_RATE_SCHEMA = StructType(
    [
        StructField('CONVERSION_DT', DateType(), False),
        StructField('FROM_CURRENCY', StringType(), False),
        StructField('TO_CURRENCY', StringType(), False),
        StructField('FX_RATE', DecimalType(28, 12), False),
    ]
)


COUNTERPARTY_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('CPTY_REF_ID', StringType(), False),
        StructField('CLIENT_ID', StringType(), False),
        StructField('CPTY_NM', StringType(), False),
        StructField('CLIENT_ID_TYPE', StringType(), False),
    ]
)
