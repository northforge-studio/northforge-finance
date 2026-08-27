from pyspark.sql.types import (
    DateType,
    DecimalType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


SEGMENT_DEFAULT_SCHEMA = StructType([
    StructField('SEGMENT_TYPE', StringType(), False),
    StructField('CONTEXT_TYPE', StringType(), False),
    StructField('CONTEXT_VALUE', StringType(), False),
    StructField('DEFAULT_VALUE', StringType(), False),
])


# UUID columns (GL_POSTING_ID, WORKFLOW_RUN_ID, PRODUCER_RUN_ID) are
# represented as StringType, matching the convention already used for
# WORKFLOW_RUN_ID/PRODUCER_RUN_ID in foundry/contracts/trial_balance.py.
POSTING_SCHEMA = StructType([
    StructField('GL_POSTING_ID', StringType(), False),
    StructField('POSTED_AT', TimestampType(), False),

    StructField('WORKFLOW_RUN_ID', StringType(), False),
    StructField('PRODUCER_RUN_ID', StringType(), False),

    StructField('DATACLASS', StringType(), False),

    StructField('TRANSACTION_NUMBER', StringType(), False),
    StructField('LINE_NUMBER', StringType(), False),

    StructField('FOUNDRY_RULE_ID', StringType(), False),
    StructField('POSTING_ID', StringType(), False),
    StructField('POSTING_STREAM', StringType(), False),

    StructField('SRC_RECORD_ID', StringType(), False),
    StructField('BATCH_ID', IntegerType(), False),
    StructField('SRC_APP_CD', StringType(), False),

    StructField('ENTITY_CD', StringType(), False),
    StructField('DEPT_CD', StringType(), False),
    StructField('BRANCH_CD', StringType(), False),
    StructField('GL_ACCOUNT', StringType(), False),
    StructField('SUB_ACCOUNT', StringType(), False),
    StructField('AFFILIATE_CD', StringType(), False),
    StructField('PRODUCT_CD', StringType(), False),
    StructField('BOOK_CD', StringType(), False),
    StructField('SOURCE_CD', StringType(), False),

    StructField('CR_DR_IND', StringType(), False),

    StructField('TRANSACTION_CURRENCY', StringType(), False),
    StructField('TRANSACTION_AMOUNT', DecimalType(28, 12), False),

    StructField('ACCOUNTED_CURRENCY', StringType(), False),
    StructField('ACCOUNTED_AMOUNT', DecimalType(28, 12), False),

    StructField('FX_RATE', DecimalType(28, 12), False),

    StructField('AS_OF_DATE', DateType(), False),
    StructField('BUSINESS_DATE', DateType(), False),
])
