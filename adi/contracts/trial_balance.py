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
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCOUNT_NM', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),

        StructField(
            'SRC_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),

        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        StructField('CPTY_REF_ID', StringType(), True),
    ]
)


TRIAL_BALANCE_STAGING_SCHEMA = StructType(
    [
        StructField('BATCH_ID', IntegerType(), False),
        StructField('EXTRACT_DT', DateType(), False),
        StructField('AS_OF_DT', DateType(), False),
        StructField('BUSINESS_DT', DateType(), False),

        StructField('SRC_APP_CD', StringType(), False),
        StructField('SRC_APP_NM', StringType(), False),
        StructField('SRC_RECORD_ID', StringType(), False),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCOUNT_NM', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),

        StructField(
            'SRC_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),

        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        StructField('CPTY_REF_ID', StringType(), True),

        StructField('STAGING_ID', StringType(), True),
        StructField('DATACLASS', StringType(), True),
        StructField('POSTING_RULE_ID', StringType(), True),
        StructField('COA_RULE_ID', StringType(), True),
        StructField('ENTITY_SUN_ID', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGROUP_IND', StringType(), True),
        StructField('POSTING_MEASURE_NM', StringType(), True),
        StructField('MEASURE_TYPE', StringType(), True),
        StructField(
            'POSTING_MEASURE_FUNC_CCY_CD',
            StringType(),
            True,
        ),
        StructField(
            'POSTING_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            True,
        ),
        StructField(
            'FX_RATE',
            DecimalType(28, 12),
            True,
        ),
        StructField(
            'POSTING_MEASURE_FUNC_AMT',
            DecimalType(28, 12),
            True,
        ),
        StructField('CR_DR_EVALUATOR', StringType(), True),
    ]
)
