from decimal import Decimal
from uuid import uuid4

from gl.contracts import INTERFACE_TRIAL_BALANCE_SCHEMA, POSTING_SCHEMA

from tests.support.constants import BUSINESS_DT, TIMESTAMP


def make_interface_values(workflow_run_id, **overrides) -> tuple:
    values = dict(
        WORKFLOW_RUN_ID=str(workflow_run_id),
        PRODUCER_RUN_ID=str(uuid4()),
        DATACLASS='TRIAL_BALANCE',
        TRANSACTION_NUMBER='TXN-1',
        LINE_NUMBER='1',
        ENTITY_CD='USM',
        DEPT_CD='4000',
        BRANCH_CD='100',
        GL_ACCOUNT='123456',
        SUB_ACCOUNT='001',
        AFFILIATE_CD='AFF1',
        PRODUCT_CD='PRD1',
        BOOK_CD='BK1',
        SOURCE_CD='SRC1',
        CR_DR_IND='DR',
        FOUNDRY_RULE_ID='RULE-1',
        POSTING_ID='POST-1',
        POSTING_STREAM='STREAM-1',
        SRC_RECORD_ID='REC-1',
        SRC_APP_CD='NFM',
        TRANSACTION_CURRENCY='USD',
        TRANSACTION_AMOUNT=Decimal('100.00'),
        ACCOUNTED_CURRENCY='USD',
        ACCOUNTED_AMOUNT=Decimal('100.00'),
        FX_RATE=Decimal('1.0'),
        AS_OF_DATE=BUSINESS_DT,
        BUSINESS_DATE=BUSINESS_DT,
    )
    values.update(overrides)
    return tuple(values[name] for name in INTERFACE_TRIAL_BALANCE_SCHEMA.fieldNames())


def make_posting_values(workflow_run_id, **overrides) -> tuple:
    values = dict(
        GL_POSTING_ID=str(uuid4()),
        POSTED_AT=TIMESTAMP,
        WORKFLOW_RUN_ID=str(workflow_run_id),
        PRODUCER_RUN_ID=str(uuid4()),
        DATACLASS='TRIAL_BALANCE',
        TRANSACTION_NUMBER='TXN-1',
        LINE_NUMBER='1',
        FOUNDRY_RULE_ID='RULE-1',
        POSTING_ID='POST-1',
        POSTING_STREAM='STREAM-1',
        SRC_RECORD_ID='REC-1',
        SRC_APP_CD='NFM',
        ENTITY_CD='USM',
        DEPT_CD='4000',
        BRANCH_CD='100',
        GL_ACCOUNT='123456',
        SUB_ACCOUNT='001',
        AFFILIATE_CD='AFF1',
        PRODUCT_CD='PRD1',
        BOOK_CD='BK1',
        SOURCE_CD='SRC1',
        CR_DR_IND='DR',
        TRANSACTION_CURRENCY='USD',
        TRANSACTION_AMOUNT=Decimal('100.00'),
        ACCOUNTED_CURRENCY='USD',
        ACCOUNTED_AMOUNT=Decimal('100.00'),
        FX_RATE=Decimal('1.0'),
        AS_OF_DATE=BUSINESS_DT,
        BUSINESS_DATE=BUSINESS_DT,
    )
    values.update(overrides)
    return tuple(values[name] for name in POSTING_SCHEMA.fieldNames())
