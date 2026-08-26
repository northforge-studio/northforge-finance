"""create trial balance zone tables

Revision ID: 3e1ac48afe80
Revises: 2e93dbffb6d4
Create Date: 2026-08-25 23:13:31.998240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3e1ac48afe80'
down_revision: Union[str, Sequence[str], None] = '2e93dbffb6d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Column definitions as (name, type_factory, nullable) tuples, mirroring
# foundry/contracts/trial_balance.py field-for-field. sa.Column instances
# cannot be shared across tables, so each table is built by materializing
# fresh columns from these tuples via `_columns()`.

_MEASURE_CORE = [
    ('src_measure_nm', sa.String, False),
    ('src_measure_ccy_cd', sa.String, False),
    ('src_measure_trans_amt', lambda: sa.Numeric(28, 12), False),
    ('posting_measure_ccy_cd', sa.String, False),
    ('posting_measure_nm', sa.String, False),
    ('measure_type', sa.String, False),
    ('posting_measure_func_ccy_cd', sa.String, False),
    ('posting_measure_trans_amt', lambda: sa.Numeric(28, 12), False),
    ('fx_rate', lambda: sa.Numeric(28, 12), False),
    ('posting_measure_func_amt', lambda: sa.Numeric(28, 12), False),
]

_RUN_IDENTITY = [
    ('workflow_run_id', lambda: postgresql.UUID(as_uuid=True), False),
    ('producer_run_id', lambda: postgresql.UUID(as_uuid=True), False),
]

_STAGING_FIELDS = [
    ('batch_id', sa.Integer, False),
    ('as_of_dt', sa.Date, False),
    ('business_dt', sa.Date, False),
    ('src_app_cd', sa.String, False),
    ('dataclass', sa.String, False),
    ('src_record_id', sa.String, False),
    ('src_entity_cd', sa.String, False),
    ('src_booking_dept_cd', sa.String, False),
    ('src_account_id', sa.String, False),
    ('src_acct_type', sa.String, False),
    ('norm_acct_sign', sa.String, False),
    ('src_client_id', sa.String, False),
    ('cpty_ref_id', sa.String, False),
    ('entity_sun_id', sa.String, False),
    ('client_id_type', sa.String, False),
    ('intergroup_ind', sa.String, False),
    *_MEASURE_CORE,
    ('cr_dr_evaluator', sa.String, False),
    *_RUN_IDENTITY,
]

_ENRICHMENT_TAIL = [
    ('cr_dr_ind', sa.String, False),
    ('posting_rule_id', sa.String, False),
    ('posting_stream', sa.String, False),
    ('posting_switch', sa.String, False),
    ('measure_period_type', sa.String, False),
    ('posting_elig_flg', sa.String, False),
    ('trans_group_prefix', sa.String, False),
    ('trans_dt', sa.String, False),
    ('trans_no', sa.String, False),
    ('line_no', sa.String, False),
    ('coa_rule_id', sa.String, False),
    ('gl_entity_cd', sa.String, False),
    ('gl_dept_cd', sa.String, False),
    ('gl_branch_cd', sa.String, False),
    ('gl_account_dr', sa.String, False),
    ('gl_account_cr', sa.String, False),
    ('gl_account', sa.String, False),
    ('gl_sub_account', sa.String, False),
    ('gl_affiliate_cd', sa.String, False),
    ('gl_product_cd', sa.String, False),
    ('gl_book_cd', sa.String, False),
    ('gl_coa_src_segment', sa.String, False),
]

# staging fields without the trailing run-identity pair.
_STAGING_BODY = _STAGING_FIELDS[:-2]

_ENRICHMENT_FIELDS = [
    *_STAGING_BODY,
    *_ENRICHMENT_TAIL,
    *_RUN_IDENTITY,
]

_ENRICHMENT_BODY = _ENRICHMENT_FIELDS[:-2]

# Reporting has no zone-lineage ID of its own; it carries the same fields
# as enrichment.
_REPORTING_FIELDS = [
    *_ENRICHMENT_BODY,
    *_RUN_IDENTITY,
]

_REPORTING_BODY = _REPORTING_FIELDS[:-2]

_BALANCE_FIELDS = [
    ('previous_day_balance', lambda: sa.Numeric(28, 12), False),
    ('current_day_debit_balance', lambda: sa.Numeric(28, 12), False),
    ('current_day_credit_balance', lambda: sa.Numeric(28, 12), False),
    ('current_day_eod_balance', lambda: sa.Numeric(28, 12), False),
    ('back_value_adjusted_balance', lambda: sa.Numeric(28, 12), False),
    ('adjusted_balance', lambda: sa.Numeric(28, 12), False),
    ('posting_previous_day_balance', lambda: sa.Numeric(28, 12), False),
    ('posting_current_day_debit_balance', lambda: sa.Numeric(28, 12), False),
    ('posting_current_day_credit_balance', lambda: sa.Numeric(28, 12), False),
    ('posting_current_day_eod_balance', lambda: sa.Numeric(28, 12), False),
    ('posting_back_value_adjusted_balance', lambda: sa.Numeric(28, 12), False),
    ('posting_adjusted_balance', lambda: sa.Numeric(28, 12), False),
]

_POSTING_FIELDS = [
    *_REPORTING_BODY[:6],
    ('posting_id', sa.String, False),
    *_REPORTING_BODY[6:],
    *_BALANCE_FIELDS,
    *_RUN_IDENTITY,
]


def _columns(fields):
    return [
        sa.Column(name, type_factory(), nullable=nullable)
        for name, type_factory, nullable in fields
    ]


_ZONE_TABLES = {
    'foundry_staging': _STAGING_FIELDS,
    'foundry_enrichment': _ENRICHMENT_FIELDS,
    'foundry_reporting': _REPORTING_FIELDS,
    'foundry_posting': _POSTING_FIELDS,
}


def upgrade() -> None:
    for schema, fields in _ZONE_TABLES.items():
        op.create_table(
            'trial_balance',
            *_columns(fields),
            sa.ForeignKeyConstraint(
                ['workflow_run_id'],
                ['core.workflow_run.workflow_run_id'],
            ),
            sa.ForeignKeyConstraint(
                ['producer_run_id'],
                ['core.execution_run.run_id'],
            ),
            schema=schema,
        )

        op.create_index(
            f'ix_{schema}_trial_balance_business_dt_batch_id',
            'trial_balance',
            ['business_dt', 'batch_id'],
            schema=schema,
        )


def downgrade() -> None:
    for schema in reversed(list(_ZONE_TABLES)):
        op.drop_index(
            f'ix_{schema}_trial_balance_business_dt_batch_id',
            table_name='trial_balance',
            schema=schema,
        )
        op.drop_table('trial_balance', schema=schema)
