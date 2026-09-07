from pyspark.sql.types import (
    DateType,
    StringType,
    StructField,
    StructType,
)

from registry.models import GLSegmentType


ENTITY_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('ENT_CD', StringType(), False),
        StructField('ENT_DS', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


BRANCH_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('BCH_CD', StringType(), False),
        StructField('BCH_DS', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


DEPARTMENT_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('DEPT_CD', StringType(), False),
        StructField('DEPT_DS', StringType(), False),
        StructField('ENT_CD', StringType(), False),
        StructField('BCH_CD', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


ACCOUNT_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('ACCT_CD', StringType(), False),
        StructField('ACCT_DS', StringType(), False),
        StructField('SUSPNS_IN', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


SUB_ACCOUNT_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('SUB_ACCT_CD', StringType(), False),
        StructField('SUB_ACCT_DS', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


AFFILIATE_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('AFFIL_CD', StringType(), False),
        StructField('AFFIL_DS', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


PRODUCT_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('PROD_CD', StringType(), False),
        StructField('PROD_DS', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


BOOK_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('BK_CD', StringType(), False),
        StructField('BK_DS', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


SOURCE_SCHEMA = StructType(
    [
        StructField('BUSINESS_DT', DateType(), False),
        StructField('SRCE_CD', StringType(), False),
        StructField('SRCE_DS', StringType(), False),
        StructField('STATUS', StringType(), False),
    ]
)


SEGMENT_SCHEMAS: dict[GLSegmentType, StructType] = {
    GLSegmentType.ENTITY: ENTITY_SCHEMA,
    GLSegmentType.BRANCH: BRANCH_SCHEMA,
    GLSegmentType.DEPARTMENT: DEPARTMENT_SCHEMA,
    GLSegmentType.ACCOUNT: ACCOUNT_SCHEMA,
    GLSegmentType.SUB_ACCOUNT: SUB_ACCOUNT_SCHEMA,
    GLSegmentType.AFFILIATE: AFFILIATE_SCHEMA,
    GLSegmentType.PRODUCT: PRODUCT_SCHEMA,
    GLSegmentType.BOOK: BOOK_SCHEMA,
    GLSegmentType.SOURCE: SOURCE_SCHEMA,
}


SEGMENT_CODE_COLUMNS: dict[GLSegmentType, str] = {
    GLSegmentType.ENTITY: 'ENT_CD',
    GLSegmentType.BRANCH: 'BCH_CD',
    GLSegmentType.DEPARTMENT: 'DEPT_CD',
    GLSegmentType.ACCOUNT: 'ACCT_CD',
    GLSegmentType.SUB_ACCOUNT: 'SUB_ACCT_CD',
    GLSegmentType.AFFILIATE: 'AFFIL_CD',
    GLSegmentType.PRODUCT: 'PROD_CD',
    GLSegmentType.BOOK: 'BK_CD',
    GLSegmentType.SOURCE: 'SRCE_CD',
}
