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
        StructField('CPTY_REF_ID', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),
        StructField('SRC_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),
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

        StructField('TOTAL_ACCT_FUNC_AMT', DecimalType(28, 12), False),
        StructField('ACCT_FUNC_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),
        StructField('ENTITY_SUN_ID', StringType(), True),
        StructField('CPTY_REF_ID', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGROUP_IND', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),
        StructField('SRC_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        StructField('POSTING_MEASURE_NM', StringType(), True),
        StructField('MEASURE_TYPE', StringType(), True),
        StructField('POSTING_MEASURE_FUNC_CCY_CD', StringType(), True),
        StructField('POSTING_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('FX_RATE', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_FUNC_AMT', DecimalType(28, 12), False),

        StructField('CR_DR_EVALUATOR', StringType(), True),

        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),
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

        StructField('TOTAL_ACCT_FUNC_AMT', DecimalType(28, 12), False),
        StructField('ACCT_FUNC_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),
        StructField('ENTITY_SUN_ID', StringType(), True),
        StructField('CPTY_REF_ID', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGROUP_IND', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),
        StructField('SRC_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        StructField('POSTING_MEASURE_NM', StringType(), True),
        StructField('MEASURE_TYPE', StringType(), True),
        StructField('POSTING_MEASURE_FUNC_CCY_CD', StringType(), True),
        StructField('POSTING_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('FX_RATE', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_FUNC_AMT', DecimalType(28, 12), False),

        StructField('CR_DR_EVALUATOR', StringType(), True),
        StructField('CR_DR_IND', StringType(), True),

        StructField('POSTING_RULE_ID', StringType(), True),
        StructField('RULE_ID_DESC', StringType(), True),
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
        StructField('GL_PRODUCT_CD', StringType(), True),
        StructField('GL_BOOK_CD', StringType(), True),
        StructField('GL_COA_SRC_SEGMENT', StringType(), True),

        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),
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

        StructField('TOTAL_ACCT_FUNC_AMT', DecimalType(28, 12), False),
        StructField('ACCT_FUNC_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),
        StructField('ENTITY_SUN_ID', StringType(), True),
        StructField('CPTY_REF_ID', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGROUP_IND', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),
        StructField('SRC_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        StructField('POSTING_MEASURE_NM', StringType(), True),
        StructField('MEASURE_TYPE', StringType(), True),
        StructField('POSTING_MEASURE_FUNC_CCY_CD', StringType(), True),
        StructField('POSTING_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('FX_RATE', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_FUNC_AMT', DecimalType(28, 12), False),

        StructField('CR_DR_EVALUATOR', StringType(), True),
        StructField('CR_DR_IND', StringType(), True),

        StructField('POSTING_RULE_ID', StringType(), True),
        StructField('RULE_ID_DESC', StringType(), True),
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
        StructField('GL_PRODUCT_CD', StringType(), True),
        StructField('GL_COA_SRC_SEGMENT', StringType(), True),

        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),
    ]
)


TRIAL_BALANCE_POSTING_SCHEMA = StructType(
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
        StructField('POSTING_ID', StringType(), True),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCOUNT_NM', StringType(), False),
        StructField('SRC_ACCT_CATEGORY', StringType(), False),
        StructField('SRC_ACCT_TYPE', StringType(), False),
        StructField('NORM_ACCT_SIGN', StringType(), False),

        StructField('TOTAL_ACCT_FUNC_AMT', DecimalType(28, 12), False),
        StructField('ACCT_FUNC_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('SRC_CLIENT_NM', StringType(), True),
        StructField('ENTITY_SUN_ID', StringType(), True),
        StructField('CPTY_REF_ID', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGROUP_IND', StringType(), True),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),
        StructField('SRC_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        StructField('POSTING_MEASURE_NM', StringType(), True),
        StructField('MEASURE_TYPE', StringType(), True),
        StructField('POSTING_MEASURE_FUNC_CCY_CD', StringType(), True),
        StructField('POSTING_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('FX_RATE', DecimalType(28, 12), False),
        StructField('POSTING_MEASURE_FUNC_AMT', DecimalType(28, 12), False),

        StructField('CR_DR_EVALUATOR', StringType(), True),
        StructField('CR_DR_IND', StringType(), True),

        StructField('POSTING_RULE_ID', StringType(), True),
        StructField('RULE_ID_DESC', StringType(), True),
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
        StructField('GL_PRODUCT_CD', StringType(), True),
        StructField('GL_BOOK_CD', StringType(), True),
        StructField('GL_COA_SRC_SEGMENT', StringType(), True),

        StructField('PREVIOUS_DAY_BALANCE', DecimalType(28, 12), False),
        StructField('CURRENT_DAY_DEBIT_BALANCE', DecimalType(28, 12), False),
        StructField('CURRENT_DAY_CREDIT_BALANCE', DecimalType(28, 12), False),
        StructField('CURRENT_DAY_EOD_BALANCE', DecimalType(28, 12), False),
        StructField('BACK_VALUE_ADJUSTED_BALANCE', DecimalType(28, 12), False),
        StructField('ADJUSTED_BALANCE', DecimalType(28, 12), False),

        StructField('POSTING_PREVIOUS_DAY_BALANCE', DecimalType(28, 12), False),
        StructField('POSTING_CURRENT_DAY_DEBIT_BALANCE', DecimalType(28, 12), False),
        StructField('POSTING_CURRENT_DAY_CREDIT_BALANCE', DecimalType(28, 12), False),
        StructField('POSTING_CURRENT_DAY_EOD_BALANCE', DecimalType(28, 12), False),
        StructField('POSTING_BACK_VALUE_ADJUSTED_BALANCE', DecimalType(28, 12), True),
        StructField('POSTING_ADJUSTED_BALANCE', DecimalType(28, 12), False),

        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),
    ]
)


GL_INGESTION_TRIAL_BALANCE_SCHEMA = StructType(
    [
        # Run identity
        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),

        StructField('TRANSACTION_NUMBER', StringType(), True),
        StructField('LINE_NUMBER', StringType(), True),

        # GL attributes
        StructField('DEFAULT_CURRENCY', StringType(), False),
        StructField('ENTITY_CD', StringType(), True),
        StructField('DEPT_CD', StringType(), True),
        StructField('BRANCH_CD', StringType(), True),
        StructField('GL_ACCOUNT', StringType(), True),
        StructField('SUB_ACCOUNT', StringType(), True),
        StructField('AFFILIATE_CD', StringType(), True),
        StructField('PRODUCT_CD', StringType(), True),
        StructField('BOOK_CD', StringType(), True),
        StructField('SOURCE_CD', StringType(), True),

        # Foundry lineage
        StructField('FOUNDRY_RULE_ID', StringType(), True),
        StructField('LINE_DESCRIPTION', StringType(), True),
        StructField('POSTING_ID', StringType(), True),
        StructField('POSTING_MEASURE_NAME', StringType(), True),
        StructField('POSTING_STREAM', StringType(), True),

        # Source lineage
        StructField('SRC_RECORD_ID', StringType(), False),
        StructField('SRC_ENTITY_ID', StringType(), False),
        StructField('SRC_ACCOUNT_ID', StringType(), False),

        # Currency / account metadata
        StructField('POSTING_MEASURE_ISO_CY_CD', StringType(), False),
        StructField('POSTING_MEASURE_FUNC_CCY_CD', StringType(), True),
        StructField('SRC_ACCOUNT_DESCRIPTION', StringType(), False),
        StructField('SRC_ACCOUNT_TYPE', StringType(), False),
        StructField('SRC_ACCOUNT_CATEGORY', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),
        StructField('SRC_ACCOUNT_NORMAN_SIGNAGE', StringType(), False),

        # Client metadata
        StructField('SRC_CLIENT_ID', StringType(), True),
        StructField('CLIENT_NAME', StringType(), True),
        StructField('CLIENT_ID_TYPE', StringType(), True),
        StructField('INTERGORUP_IDENTIFIER', StringType(), True),

        StructField('ACCT_FUNC_SIGNAGE', StringType(), False),

        # Source metadata
        StructField('BATCH_ID', IntegerType(), False),
        StructField('SRC_APP_CD', StringType(), False),
        StructField('SRC_APP_NM', StringType(), False),

        # Amounts
        StructField('DEFAULT_AMOUNT', DecimalType(28, 12), False),
        StructField('ACCOUNTED_AMOUNT', DecimalType(28, 12), False),
        StructField('FX_RATE', DecimalType(28, 12), False),

        # Trial Balance measures
        StructField('SRC_PREV_DAY_BAL_AMT', DecimalType(28, 12), False),
        StructField('SRC_CRNT_DAY_DEBIT', DecimalType(28, 12), False),
        StructField('SRC_CRNT_DAY_CREDIT', DecimalType(28, 12), False),
        StructField('SRC_CRNT_DAY_EOD_BALANCE', DecimalType(28, 12), False),
        StructField(
            'SRC_BACK_VALUED_ADJUSTMENT',
            DecimalType(28, 12),
            False,
        ),
        StructField('SRC_MEASURE_TRANS_AMT', DecimalType(28, 12), False),
        StructField('SRC_ACCT_FUNC_AMT', DecimalType(28, 12), False),

        # Dates
        StructField('AS_OF_DATE', DateType(), False),
        StructField('EXTRACT_DATE', DateType(), False),
    ]
)
