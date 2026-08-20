from pyspark.sql.types import (
    DateType,
    DecimalType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)


TRIAL_BALANCE_SOURCE_SCHEMA = StructType(
    [
        StructField('BATCH_ID', IntegerType(), False),
        StructField('EXTRACT_DT', DateType(), False),
        StructField('AS_OF_DT', DateType(), False),
        StructField('BUSINESS_DT', DateType(), False),

        StructField('SRC_APP_CD', StringType(), False),
        StructField('SRC_APP_NM', StringType(), False),
        StructField('SRC_RECORD_ID', StringType(), False),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', IntegerType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCOUNT_NM', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),
        StructField('SRC_CLIENT_ID_TYPE', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),

        StructField(
            'SRC_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),

        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),
    ]
)