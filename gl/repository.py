from datetime import date
from uuid import UUID

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from core.store import Store

from gl.contracts import (
    INTERFACE_TRIAL_BALANCE_SCHEMA,
    POSTING_SCHEMA,
    REJECTION_SCHEMA,
    SEGMENT_DEFAULT_SCHEMA,
)
from gl.models import GLInstruction, GLPosting, GLRejection, SegmentDefault


class GLRepository:
    def __init__(self, store: Store, spark: SparkSession):
        self._store = store
        self._spark = spark


    def get_segment_default(
        self,
        segment_type: str,
        context_type: str,
        context_value: str,
    ) -> SegmentDefault | None:
        df = self._store.read(
            table_name='SEGMENT_DEFAULT',
            schema=SEGMENT_DEFAULT_SCHEMA,
        )

        rows = (
            df
            .filter(
                (F.col('SEGMENT_TYPE') == segment_type)
                & (F.col('CONTEXT_TYPE') == context_type)
                & (F.col('CONTEXT_VALUE') == context_value)
            )
            .collect()
        )

        if not rows:
            return None

        row = rows[0]

        return SegmentDefault(
            segment_type=row['SEGMENT_TYPE'],
            context_type=row['CONTEXT_TYPE'],
            context_value=row['CONTEXT_VALUE'],
            default_value=row['DEFAULT_VALUE'],
        )


    def write_posting(self, posting: GLPosting) -> None:
        df = self._spark.createDataFrame(
            [self._to_row(posting)],
            schema=POSTING_SCHEMA,
        )

        self._store.write(df, table_name='POSTING')


    def get_postings(
        self,
        business_dt: date,
        batch_id: int,
    ) -> tuple[GLPosting, ...]:
        df = self._store.read(
            table_name='POSTING',
            schema=POSTING_SCHEMA,
        )

        rows = (
            df
            .filter(
                (F.col('BUSINESS_DATE') == business_dt)
                & (F.col('BATCH_ID') == batch_id)
            )
            .collect()
        )

        return tuple(self._from_row(row) for row in rows)


    def write_rejection(self, rejection: GLRejection) -> None:
        df = self._spark.createDataFrame(
            [self._to_rejection_row(rejection)],
            schema=REJECTION_SCHEMA,
        )

        self._store.write(df, table_name='REJECTION')


    def get_rejections(
        self,
        business_dt: date,
        batch_id: int,
    ) -> tuple[GLRejection, ...]:
        df = self._store.read(
            table_name='REJECTION',
            schema=REJECTION_SCHEMA,
        )

        rows = (
            df
            .filter(
                (F.col('BUSINESS_DATE') == business_dt)
                & (F.col('BATCH_ID') == batch_id)
            )
            .collect()
        )

        return tuple(self._from_rejection_row(row) for row in rows)


    def get_instructions(
        self,
        business_dt: date,
        batch_id: int,
    ) -> tuple[GLInstruction, ...]:
        df = self._store.read(
            table_name='INTERFACE_TRIAL_BALANCE',
            schema=INTERFACE_TRIAL_BALANCE_SCHEMA,
        )

        rows = (
            df
            .filter(
                (F.col('BUSINESS_DATE') == business_dt)
                & (F.col('BATCH_ID') == batch_id)
            )
            .orderBy('TRANSACTION_NUMBER', 'LINE_NUMBER', 'POSTING_ID')
            .collect()
        )

        return tuple(self._from_instruction_row(row) for row in rows)


    def _to_row(self, posting: GLPosting) -> tuple:
        return (
            str(posting.gl_posting_id),
            posting.posted_at,
            str(posting.workflow_run_id),
            str(posting.producer_run_id),
            posting.dataclass,
            posting.transaction_number,
            posting.line_number,
            posting.foundry_rule_id,
            posting.posting_id,
            posting.posting_stream,
            posting.src_record_id,
            posting.batch_id,
            posting.src_app_cd,
            posting.entity_cd,
            posting.dept_cd,
            posting.branch_cd,
            posting.gl_account,
            posting.sub_account,
            posting.affiliate_cd,
            posting.product_cd,
            posting.book_cd,
            posting.source_cd,
            posting.cr_dr_ind,
            posting.transaction_currency,
            posting.transaction_amount,
            posting.accounted_currency,
            posting.accounted_amount,
            posting.fx_rate,
            posting.as_of_date,
            posting.business_date,
        )


    def _from_row(self, row) -> GLPosting:
        return GLPosting(
            gl_posting_id=UUID(row['GL_POSTING_ID']),
            posted_at=row['POSTED_AT'],
            workflow_run_id=UUID(row['WORKFLOW_RUN_ID']),
            producer_run_id=UUID(row['PRODUCER_RUN_ID']),
            dataclass=row['DATACLASS'],
            transaction_number=row['TRANSACTION_NUMBER'],
            line_number=row['LINE_NUMBER'],
            foundry_rule_id=row['FOUNDRY_RULE_ID'],
            posting_id=row['POSTING_ID'],
            posting_stream=row['POSTING_STREAM'],
            src_record_id=row['SRC_RECORD_ID'],
            batch_id=row['BATCH_ID'],
            src_app_cd=row['SRC_APP_CD'],
            entity_cd=row['ENTITY_CD'],
            dept_cd=row['DEPT_CD'],
            branch_cd=row['BRANCH_CD'],
            gl_account=row['GL_ACCOUNT'],
            sub_account=row['SUB_ACCOUNT'],
            affiliate_cd=row['AFFILIATE_CD'],
            product_cd=row['PRODUCT_CD'],
            book_cd=row['BOOK_CD'],
            source_cd=row['SOURCE_CD'],
            cr_dr_ind=row['CR_DR_IND'],
            transaction_currency=row['TRANSACTION_CURRENCY'],
            transaction_amount=row['TRANSACTION_AMOUNT'],
            accounted_currency=row['ACCOUNTED_CURRENCY'],
            accounted_amount=row['ACCOUNTED_AMOUNT'],
            fx_rate=row['FX_RATE'],
            as_of_date=row['AS_OF_DATE'],
            business_date=row['BUSINESS_DATE'],
        )


    def _to_rejection_row(self, rejection: GLRejection) -> tuple:
        return (
            str(rejection.gl_rejection_id),
            rejection.rejected_at,
            str(rejection.workflow_run_id),
            str(rejection.producer_run_id),
            rejection.dataclass,
            rejection.transaction_number,
            rejection.line_number,
            rejection.foundry_rule_id,
            rejection.posting_id,
            rejection.posting_stream,
            rejection.src_record_id,
            rejection.batch_id,
            rejection.src_app_cd,
            rejection.business_date,
            rejection.as_of_date,
            rejection.rejection_type,
            rejection.rejection_detail,
        )


    def _from_rejection_row(self, row) -> GLRejection:
        return GLRejection(
            gl_rejection_id=UUID(row['GL_REJECTION_ID']),
            rejected_at=row['REJECTED_AT'],
            workflow_run_id=UUID(row['WORKFLOW_RUN_ID']),
            producer_run_id=UUID(row['PRODUCER_RUN_ID']),
            dataclass=row['DATACLASS'],
            transaction_number=row['TRANSACTION_NUMBER'],
            line_number=row['LINE_NUMBER'],
            foundry_rule_id=row['FOUNDRY_RULE_ID'],
            posting_id=row['POSTING_ID'],
            posting_stream=row['POSTING_STREAM'],
            src_record_id=row['SRC_RECORD_ID'],
            batch_id=row['BATCH_ID'],
            src_app_cd=row['SRC_APP_CD'],
            business_date=row['BUSINESS_DATE'],
            as_of_date=row['AS_OF_DATE'],
            rejection_type=row['REJECTION_TYPE'],
            rejection_detail=row['REJECTION_DETAIL'],
        )


    def _from_instruction_row(self, row) -> GLInstruction:
        return GLInstruction(
            workflow_run_id=UUID(row['WORKFLOW_RUN_ID']),
            producer_run_id=UUID(row['PRODUCER_RUN_ID']),
            dataclass=row['DATACLASS'],
            transaction_number=row['TRANSACTION_NUMBER'],
            line_number=row['LINE_NUMBER'],
            foundry_rule_id=row['FOUNDRY_RULE_ID'],
            posting_id=row['POSTING_ID'],
            posting_stream=row['POSTING_STREAM'],
            src_record_id=row['SRC_RECORD_ID'],
            batch_id=row['BATCH_ID'],
            src_app_cd=row['SRC_APP_CD'],
            entity_cd=row['ENTITY_CD'],
            dept_cd=row['DEPT_CD'],
            branch_cd=row['BRANCH_CD'],
            gl_account=row['GL_ACCOUNT'],
            sub_account=row['SUB_ACCOUNT'],
            affiliate_cd=row['AFFILIATE_CD'],
            product_cd=row['PRODUCT_CD'],
            book_cd=row['BOOK_CD'],
            source_cd=row['SOURCE_CD'],
            cr_dr_ind=row['CR_DR_IND'],
            transaction_currency=row['TRANSACTION_CURRENCY'],
            transaction_amount=row['TRANSACTION_AMOUNT'],
            accounted_currency=row['ACCOUNTED_CURRENCY'],
            accounted_amount=row['ACCOUNTED_AMOUNT'],
            fx_rate=row['FX_RATE'],
            as_of_date=row['AS_OF_DATE'],
            business_date=row['BUSINESS_DATE'],
        )
