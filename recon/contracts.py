from pyspark.sql.types import (
    DateType,
    DecimalType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


# The grain recon is calculated and aggregated at. Shared by Phase 2's
# calculation logic (groupBy/join keys) and the recon.result persistence
# contract below (every key here, except WORKFLOW_RUN_ID, also appears
# as a RESULT_SCHEMA column).
RECON_KEYS = (
    'WORKFLOW_RUN_ID',
    'AS_OF_DATE',
    'ENTITY_CD',
    'DEPT_CD',
    'BRANCH_CD',
    'GL_ACCOUNT',
    'SUB_ACCOUNT',
    'AFFILIATE_CD',
    'PRODUCT_CD',
    'BOOK_CD',
    'SOURCE_CD',
    'ACCOUNTED_CURRENCY',
)


# The physical schema of recon.result. Column names/types mirror the
# migration in
# migrations/versions/c6d521ab213f_create_recon_result_table.py exactly,
# since that migration is the canonical source of truth for these types.
RESULT_SCHEMA = StructType([
    StructField('RECON_RESULT_ID', StringType(), False),
    StructField('RECONCILED_AT', TimestampType(), False),

    StructField('WORKFLOW_RUN_ID', StringType(), False),
    StructField('PRODUCER_RUN_ID', StringType(), False),

    StructField('AS_OF_DATE', DateType(), False),
    StructField('ENTITY_CD', StringType(), False),
    StructField('DEPT_CD', StringType(), False),
    StructField('BRANCH_CD', StringType(), False),
    StructField('GL_ACCOUNT', StringType(), False),
    StructField('SUB_ACCOUNT', StringType(), False),
    StructField('AFFILIATE_CD', StringType(), False),
    StructField('PRODUCT_CD', StringType(), False),
    StructField('BOOK_CD', StringType(), False),
    StructField('SOURCE_CD', StringType(), False),
    StructField('ACCOUNTED_CURRENCY', StringType(), False),

    StructField('INTERFACE_BALANCE', DecimalType(28, 12), False),
    StructField('GL_BALANCE', DecimalType(28, 12), False),
    StructField('DIFFERENCE_AMOUNT', DecimalType(28, 12), False),
])
