from pyspark.sql.types import (
    DateType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from registry.models import SegmentType


ENTITY_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('ENT_CD', StringType(), True),
        StructField('ENT_DS', StringType(), True),
        StructField('SUN_ID', StringType(), True),
        StructField('PARENT_ENT_1_CD', StringType(), True),
        StructField('PARENT_ENT_2_CD', StringType(), True),
        StructField('PARENT_ENT_2_NM', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


DEPARTMENT_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('DEPT_CD', StringType(), True),
        StructField('DEPT_DS', StringType(), True),
        StructField('LGCY_DEPT_CD', StringType(), True),
        StructField('PARNT_DEPT_CD', StringType(), True),
        StructField('PARNT_DEPT_DS', StringType(), True),
        StructField('ENT_CD', StringType(), True),
        StructField('ENT_NM', StringType(), True),
        StructField('BCH_CD', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


BRANCH_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('BCH_CD', StringType(), True),
        StructField('BCH_DS', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


ACCOUNT_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('ACCT_CD', StringType(), True),
        StructField('ACCT_DS', StringType(), True),
        StructField('PARNT_ACCT_CD', StringType(), True),
        StructField('PARNT_ACCT_NM', StringType(), True),
        StructField('SUSPNS_IN', StringType(), True),
        StructField('IG_IN', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


SUB_ACCOUNT_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('SUB_ACCT_CD', StringType(), True),
        StructField('SUB_ACCT_DS', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


AFFILIATE_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('AFFIL_CD', StringType(), True),
        StructField('AFFIL_DS', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


PRODUCT_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('PROD_CD', StringType(), True),
        StructField('PROD_DS', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


BOOK_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('BK_CD', StringType(), True),
        StructField('BK_DS', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


SOURCE_SCHEMA = StructType(
    [
        StructField('AUD_LOAD_ID', StringType(), True),
        StructField('BUSINESS_DT', DateType(), True),
        StructField('VER_NB', IntegerType(), True),
        StructField('SRCE_CD', StringType(), True),
        StructField('SRCE_DS', StringType(), True),
        StructField('RGN_CD', StringType(), True),
        StructField('STATUS', StringType(), True),
    ]
)


SEGMENT_SCHEMAS: dict[SegmentType, StructType] = {
    SegmentType.ENTITY: ENTITY_SCHEMA,
    SegmentType.DEPARTMENT: DEPARTMENT_SCHEMA,
    SegmentType.BRANCH: BRANCH_SCHEMA,
    SegmentType.ACCOUNT: ACCOUNT_SCHEMA,
    SegmentType.SUB_ACCOUNT: SUB_ACCOUNT_SCHEMA,
    SegmentType.AFFILIATE: AFFILIATE_SCHEMA,
    SegmentType.PRODUCT: PRODUCT_SCHEMA,
    SegmentType.BOOK: BOOK_SCHEMA,
    SegmentType.SOURCE: SOURCE_SCHEMA,
}


SEGMENT_CODE_COLUMNS: dict[SegmentType, str] = {
    SegmentType.ENTITY: 'ENT_CD',
    SegmentType.DEPARTMENT: 'DEPT_CD',
    SegmentType.BRANCH: 'BCH_CD',
    SegmentType.ACCOUNT: 'ACCT_CD',
    SegmentType.SUB_ACCOUNT: 'SUB_ACCT_CD',
    SegmentType.AFFILIATE: 'AFFIL_CD',
    SegmentType.PRODUCT: 'PROD_CD',
    SegmentType.BOOK: 'BK_CD',
    SegmentType.SOURCE: 'SRCE_CD',
}
