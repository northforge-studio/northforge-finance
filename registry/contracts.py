from pyspark.sql.types import (
    DateType,
    StringType,
    StructField,
    StructType,
)

from registry.models import SegmentType


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


SEGMENT_SCHEMAS: dict[SegmentType, StructType] = {
    SegmentType.ENTITY: ENTITY_SCHEMA,
    SegmentType.BRANCH: BRANCH_SCHEMA,
    SegmentType.DEPARTMENT: DEPARTMENT_SCHEMA,
    SegmentType.ACCOUNT: ACCOUNT_SCHEMA,
    SegmentType.SUB_ACCOUNT: SUB_ACCOUNT_SCHEMA,
    SegmentType.AFFILIATE: AFFILIATE_SCHEMA,
    SegmentType.PRODUCT: PRODUCT_SCHEMA,
    SegmentType.BOOK: BOOK_SCHEMA,
    SegmentType.SOURCE: SOURCE_SCHEMA,
}


SEGMENT_CODE_COLUMNS: dict[SegmentType, str] = {
    SegmentType.ENTITY: 'ENT_CD',
    SegmentType.BRANCH: 'BCH_CD',
    SegmentType.DEPARTMENT: 'DEPT_CD',
    SegmentType.ACCOUNT: 'ACCT_CD',
    SegmentType.SUB_ACCOUNT: 'SUB_ACCT_CD',
    SegmentType.AFFILIATE: 'AFFIL_CD',
    SegmentType.PRODUCT: 'PROD_CD',
    SegmentType.BOOK: 'BK_CD',
    SegmentType.SOURCE: 'SRCE_CD',
}
