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
        StructField('SRC_ACCT_CATEGORY', StringType(), False),
        StructField('SRC_ACCT_TYPE', StringType(), False),
        StructField('NORM_ACCT_SIGN', StringType(), False),

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
        StructField('DATACLASS', StringType(), True),

        StructField('SRC_RECORD_ID', StringType(), False),
        StructField('STAGING_ID', StringType(), True),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCOUNT_NM', StringType(), False),
        StructField('SRC_ACCT_CATEGORY', StringType(), False),
        StructField('SRC_ACCT_TYPE', StringType(), False),
        StructField('NORM_ACCT_SIGN', StringType(), False),

        StructField(
            'TOTAL_ACCT_FUNC_AMT', 
            DecimalType(28, 12),
            False
        ),
        StructField('ACCT_FUNC_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),
        StructField('ENTITY_SUN_ID', StringType(), True),
        StructField('CPTY_REF_ID', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGROUP_IND', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),

        StructField(
            'SRC_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),

        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),
        
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


TRIAL_BALANCE_ENRICHMENT_SCHEMA = StructType(
    [
        StructField('BATCH_ID', IntegerType(), False),
        StructField('EXTRACT_DT', DateType(), False),
        StructField('AS_OF_DT', DateType(), False),
        StructField('BUSINESS_DT', DateType(), False),

        StructField('SRC_APP_CD', StringType(), False),
        StructField('SRC_APP_NM', StringType(), False),
        StructField('DATACLASS', StringType(), True),

        StructField('SRC_RECORD_ID', StringType(), False),
        StructField('STAGING_ID', StringType(), True),
        StructField('ENRICHMENT_ID', StringType(), True),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCOUNT_NM', StringType(), False),
        StructField('SRC_ACCT_CATEGORY', StringType(), False),
        StructField('SRC_ACCT_TYPE', StringType(), False),
        StructField('NORM_ACCT_SIGN', StringType(), False),

        StructField(
            'TOTAL_ACCT_FUNC_AMT', 
            DecimalType(28, 12),
            False
        ),
        StructField('ACCT_FUNC_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),
        StructField('ENTITY_SUN_ID', StringType(), True),
        StructField('CPTY_REF_ID', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGROUP_IND', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),

        StructField(
            'SRC_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),

        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        
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
        StructField('CR_DR_IND', StringType(), True),

        StructField('POSTING_RULE_ID', StringType(), True),
        StructField('POSTING_STREAM', StringType(), True),
        StructField('POSTING_SWITCH', StringType(), True),
        StructField('MEASURE_PERIOD_TYPE', StringType(), True),
        StructField('POSTING_ELIG_FLG', StringType(), True),
        
        StructField('JE_DESC', StringType(), True),
        StructField('EVENT_TYPE_CD', StringType(), True),
        StructField('TRANS_GROUP_PREFIX', StringType(), True),
        StructField('TRANS_DT', StringType(), True),
        StructField('TRANS_NO', StringType(), True),
        StructField('LINE_NO', StringType(), True),

        StructField('COA_RULE_ID', StringType(), True),
        StructField('GL_ENTITY_CD', StringType(), True),
        StructField('GL_DEPT_CD', StringType(), True),
        StructField('GL_BRANCH_CD', StringType(), True),
        StructField('GL_ACCOUNT_DR', StringType(), True),
        StructField('GL_ACCOUNT_DR_DESC', StringType(), True),
        StructField('GL_ACCOUNT_CR', StringType(), True),
        StructField('GL_ACCOUNT_CR_DESC', StringType(), True),
        StructField('GL_ACCOUNT', StringType(), True),
        StructField('GL_SUB_ACCOUNT', StringType(), True),
        StructField('GL_AFFILIATE_CD', StringType(), True),
        StructField('GL_BOOK_CD', StringType(), True),
        StructField('GL_COA_SRC_SEGMENT', StringType(), True),
        StructField('GL_PRODUCT_CD', StringType(), True),
    ]
)


TRIAL_BALANCE_REPORTING_SCHEMA = StructType(
    [
        StructField('BATCH_ID', IntegerType(), False),
        StructField('EXTRACT_DT', DateType(), False),
        StructField('AS_OF_DT', DateType(), False),
        StructField('BUSINESS_DT', DateType(), False),

        StructField('SRC_APP_CD', StringType(), False),
        StructField('SRC_APP_NM', StringType(), False),
        StructField('DATACLASS', StringType(), True),

        StructField('SRC_RECORD_ID', StringType(), False),
        StructField('STAGING_ID', StringType(), True),
        StructField('ENRICHMENT_ID', StringType(), True),
        StructField('REPORTING_ID', StringType(), True),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCOUNT_NM', StringType(), False),
        StructField('SRC_ACCT_CATEGORY', StringType(), False),
        StructField('SRC_ACCT_TYPE', StringType(), False),
        StructField('NORM_ACCT_SIGN', StringType(), False),

        StructField(
            'TOTAL_ACCT_FUNC_AMT',
            DecimalType(28, 12),
            False
        ),
        StructField('ACCT_FUNC_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),
        StructField('ENTITY_SUN_ID', StringType(), True),
        StructField('CPTY_REF_ID', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGROUP_IND', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),

        StructField(
            'SRC_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),

        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),


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
        StructField('CR_DR_IND', StringType(), True),

        StructField('POSTING_RULE_ID', StringType(), True),
        StructField('POSTING_STREAM', StringType(), True),
        StructField('POSTING_SWITCH', StringType(), True),
        StructField('MEASURE_PERIOD_TYPE', StringType(), True),
        StructField('POSTING_ELIG_FLG', StringType(), True),

        StructField('JE_DESC', StringType(), True),
        StructField('EVENT_TYPE_CD', StringType(), True),
        StructField('TRANS_GROUP_PREFIX', StringType(), True),
        StructField('TRANS_DT', StringType(), True),
        StructField('TRANS_NO', StringType(), True),
        StructField('LINE_NO', StringType(), True),

        StructField('COA_RULE_ID', StringType(), True),
        StructField('GL_ENTITY_CD', StringType(), True),
        StructField('GL_DEPT_CD', StringType(), True),
        StructField('GL_BRANCH_CD', StringType(), True),
        StructField('GL_ACCOUNT_DR', StringType(), True),
        StructField('GL_ACCOUNT_DR_DESC', StringType(), True),
        StructField('GL_ACCOUNT_CR', StringType(), True),
        StructField('GL_ACCOUNT_CR_DESC', StringType(), True),
        StructField('GL_ACCOUNT', StringType(), True),
        StructField('GL_SUB_ACCOUNT', StringType(), True),
        StructField('GL_AFFILIATE_CD', StringType(), True),
        StructField('GL_BOOK_CD', StringType(), True),
        StructField('GL_COA_SRC_SEGMENT', StringType(), True),
        StructField('GL_PRODUCT_CD', StringType(), True),
    ]
)
