from pyspark.sql.types import (
    DateType,
    DecimalType,
    StringType,
    StructField,
    StructType,
)

from registry.models import GLSegmentType


TRIAL_BALANCE_SOURCE_SCHEMA = StructType(
    [
        StructField('AS_OF_DT', DateType(), False),
        StructField('BUSINESS_DT', DateType(), False),

        StructField('SRC_APP_CD', StringType(), False),
        StructField('SRC_RECORD_ID', StringType(), False),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCT_TYPE', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), False),
        StructField('CPTY_REF_ID', StringType(), False),

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


TRIAL_BALANCE_STAGING_SCHEMA = StructType(
    [
        StructField('AS_OF_DT', DateType(), False),
        StructField('BUSINESS_DT', DateType(), False),

        StructField('SRC_APP_CD', StringType(), False),
        StructField('DATACLASS', StringType(), False),

        StructField('SRC_RECORD_ID', StringType(), False),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCT_TYPE', StringType(), False),
        StructField('NORM_ACCT_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), False),
        StructField('CPTY_REF_ID', StringType(), False),
        StructField('ENTITY_SUN_ID', StringType(), False),
        StructField('CLIENT_ID_TYPE', StringType(), False),
        StructField('INTERGROUP_IND', StringType(), False),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),
        StructField(
            'SRC_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),
        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        StructField('POSTING_MEASURE_NM', StringType(), False),
        StructField('MEASURE_TYPE', StringType(), False),
        StructField(
            'POSTING_MEASURE_FUNC_CCY_CD',
            StringType(),
            False,
        ),
        StructField(
            'POSTING_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),
        StructField('FX_RATE', DecimalType(28, 12), False),
        StructField(
            'POSTING_MEASURE_FUNC_AMT',
            DecimalType(28, 12),
            False,
        ),

        StructField('CR_DR_EVALUATOR', StringType(), False),

        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),
    ]
)


TRIAL_BALANCE_ENRICHMENT_SCHEMA = StructType(
    [
        StructField('AS_OF_DT', DateType(), False),
        StructField('BUSINESS_DT', DateType(), False),

        StructField('SRC_APP_CD', StringType(), False),
        StructField('DATACLASS', StringType(), False),

        StructField('SRC_RECORD_ID', StringType(), False),

        StructField('SRC_ENTITY_CD', StringType(), False),
        StructField('SRC_BOOKING_DEPT_CD', StringType(), False),

        StructField('SRC_ACCOUNT_ID', StringType(), False),
        StructField('SRC_ACCT_TYPE', StringType(), False),
        StructField('NORM_ACCT_SIGN', StringType(), False),

        StructField('SRC_CLIENT_ID', StringType(), False),
        StructField('CPTY_REF_ID', StringType(), False),
        StructField('ENTITY_SUN_ID', StringType(), False),
        StructField('CLIENT_ID_TYPE', StringType(), False),
        StructField('INTERGROUP_IND', StringType(), False),

        StructField('SRC_MEASURE_NM', StringType(), False),
        StructField('SRC_MEASURE_CCY_CD', StringType(), False),
        StructField(
            'SRC_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),
        StructField('POSTING_MEASURE_CCY_CD', StringType(), False),

        StructField('POSTING_MEASURE_NM', StringType(), False),
        StructField('MEASURE_TYPE', StringType(), False),
        StructField(
            'POSTING_MEASURE_FUNC_CCY_CD',
            StringType(),
            False,
        ),
        StructField(
            'POSTING_MEASURE_TRANS_AMT',
            DecimalType(28, 12),
            False,
        ),
        StructField('FX_RATE', DecimalType(28, 12), False),
        StructField(
            'POSTING_MEASURE_FUNC_AMT',
            DecimalType(28, 12),
            False,
        ),

        StructField('CR_DR_EVALUATOR', StringType(), False),
        StructField('CR_DR_IND', StringType(), False),

        StructField('POSTING_RULE_ID', StringType(), False),
        StructField('POSTING_STREAM', StringType(), False),
        StructField('POSTING_SWITCH', StringType(), False),
        StructField('MEASURE_PERIOD_TYPE', StringType(), False),
        StructField('POSTING_ELIG_FLG', StringType(), False),

        StructField('TRANS_GROUP_PREFIX', StringType(), False),
        StructField('TRANS_DT', StringType(), False),
        StructField('TRANS_NO', StringType(), False),
        StructField('LINE_NO', StringType(), False),

        StructField('COA_RULE_ID', StringType(), False),

        StructField('GL_ENTITY_CD', StringType(), False),
        StructField('GL_BRANCH_CD', StringType(), False),
        StructField('GL_DEPT_CD', StringType(), False),

        StructField('GL_ACCOUNT_DR', StringType(), False),
        StructField('GL_ACCOUNT_CR', StringType(), False),
        StructField('GL_ACCOUNT', StringType(), False),

        StructField('GL_SUB_ACCOUNT', StringType(), False),
        StructField('GL_AFFILIATE_CD', StringType(), False),
        StructField('GL_PRODUCT_CD', StringType(), False),
        StructField('GL_BOOK_CD', StringType(), False),
        StructField('GL_COA_SRC_SEGMENT', StringType(), False),

        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),
    ]
)


TRIAL_BALANCE_REPORTING_SCHEMA = StructType(
    [
        *TRIAL_BALANCE_ENRICHMENT_SCHEMA.fields,
    ]
)


TRIAL_BALANCE_POSTING_SCHEMA = StructType(
    [
        *TRIAL_BALANCE_REPORTING_SCHEMA.fields[:5],

        StructField('POSTING_ID', StringType(), False),

        *TRIAL_BALANCE_REPORTING_SCHEMA.fields[5:-2],

        StructField(
            'PREVIOUS_DAY_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'CURRENT_DAY_DEBIT_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'CURRENT_DAY_CREDIT_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'CURRENT_DAY_EOD_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'BACK_VALUE_ADJUSTED_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'ADJUSTED_BALANCE',
            DecimalType(28, 12),
            False,
        ),

        StructField(
            'POSTING_PREVIOUS_DAY_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'POSTING_CURRENT_DAY_DEBIT_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'POSTING_CURRENT_DAY_CREDIT_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'POSTING_CURRENT_DAY_EOD_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'POSTING_BACK_VALUE_ADJUSTED_BALANCE',
            DecimalType(28, 12),
            False,
        ),
        StructField(
            'POSTING_ADJUSTED_BALANCE',
            DecimalType(28, 12),
            False,
        ),

        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),
    ]
)


# Physical TRIAL_BALANCE_POSTING_SCHEMA / TRIAL_BALANCE_ENRICHMENT_SCHEMA
# column carrying each GL segment. GLSegmentType itself only carries the
# Registry segment code and the GLSegments/Interface attribute name
# (registry.models.GLSegmentType), neither of which is the foundry_posting
# column name, so that correspondence is kept here. It is cross-checked
# against data/spec/file_layout.csv, which independently confirms the same
# posting-column -> interface-column pairing.
TRIAL_BALANCE_POSTING_SEGMENT_COLUMNS: dict[GLSegmentType, str] = {
    GLSegmentType.ENTITY: 'GL_ENTITY_CD',
    GLSegmentType.BRANCH: 'GL_BRANCH_CD',
    GLSegmentType.DEPARTMENT: 'GL_DEPT_CD',
    GLSegmentType.ACCOUNT: 'GL_ACCOUNT',
    GLSegmentType.SUB_ACCOUNT: 'GL_SUB_ACCOUNT',
    GLSegmentType.AFFILIATE: 'GL_AFFILIATE_CD',
    GLSegmentType.PRODUCT: 'GL_PRODUCT_CD',
    GLSegmentType.BOOK: 'GL_BOOK_CD',
    GLSegmentType.SOURCE: 'GL_COA_SRC_SEGMENT',
}


TRIAL_BALANCE_INTERFACE_SCHEMA = StructType(
    [
        StructField('WORKFLOW_RUN_ID', StringType(), False),
        StructField('PRODUCER_RUN_ID', StringType(), False),

        StructField('DATACLASS', StringType(), False),

        StructField('TRANSACTION_NUMBER', StringType(), False),
        StructField('LINE_NUMBER', StringType(), False),

        StructField('ENTITY_CD', StringType(), False),
        StructField('BRANCH_CD', StringType(), False),
        StructField('DEPT_CD', StringType(), False),
        StructField('GL_ACCOUNT', StringType(), False),
        StructField('SUB_ACCOUNT', StringType(), False),
        StructField('AFFILIATE_CD', StringType(), False),
        StructField('PRODUCT_CD', StringType(), False),
        StructField('BOOK_CD', StringType(), False),
        StructField('SOURCE_CD', StringType(), False),

        StructField('CR_DR_IND', StringType(), False),

        StructField('FOUNDRY_RULE_ID', StringType(), False),
        StructField('POSTING_ID', StringType(), False),
        StructField('POSTING_STREAM', StringType(), False),

        StructField('SRC_RECORD_ID', StringType(), False),
        StructField('SRC_APP_CD', StringType(), False),

        StructField('TRANSACTION_CURRENCY', StringType(), False),
        StructField(
            'TRANSACTION_AMOUNT',
            DecimalType(28, 12),
            False,
        ),

        StructField('ACCOUNTED_CURRENCY', StringType(), False),
        StructField(
            'ACCOUNTED_AMOUNT',
            DecimalType(28, 12),
            False,
        ),

        StructField('FX_RATE', DecimalType(28, 12), False),

        StructField('AS_OF_DATE', DateType(), False),
        StructField('BUSINESS_DATE', DateType(), False),
    ]
)
