"""create trial balance interface table

Revision ID: 3aa94a058963
Revises: 3dc8643ac334
Create Date: 2026-08-25 13:35:38.591679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3aa94a058963'
down_revision: Union[str, Sequence[str], None] = '3dc8643ac334'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trial_balance',

        sa.Column('workflow_run_id', sa.String(), nullable=False),
        sa.Column('producer_run_id', sa.String(), nullable=False),

        sa.Column('transaction_number', sa.String(), nullable=True),
        sa.Column('line_number', sa.String(), nullable=True),

        sa.Column('default_currency', sa.String(), nullable=False),
        sa.Column('entity_cd', sa.String(), nullable=True),
        sa.Column('dept_cd', sa.String(), nullable=True),
        sa.Column('branch_cd', sa.String(), nullable=True),
        sa.Column('gl_account', sa.String(), nullable=True),
        sa.Column('sub_account', sa.String(), nullable=True),
        sa.Column('affiliate_cd', sa.String(), nullable=True),
        sa.Column('product_cd', sa.String(), nullable=True),
        sa.Column('book_cd', sa.String(), nullable=True),
        sa.Column('source_cd', sa.String(), nullable=True),

        sa.Column('foundry_rule_id', sa.String(), nullable=True),
        sa.Column('line_description', sa.String(), nullable=True),
        sa.Column('posting_id', sa.String(), nullable=True),
        sa.Column('posting_measure_name', sa.String(), nullable=True),
        sa.Column('posting_stream', sa.String(), nullable=True),

        sa.Column('src_record_id', sa.String(), nullable=False),
        sa.Column('src_entity_id', sa.String(), nullable=False),
        sa.Column('src_account_id', sa.String(), nullable=False),

        sa.Column('posting_measure_iso_cy_cd', sa.String(), nullable=False),
        sa.Column('posting_measure_func_ccy_cd', sa.String(), nullable=True),
        sa.Column('src_account_description', sa.String(), nullable=False),
        sa.Column('src_account_type', sa.String(), nullable=False),
        sa.Column('src_account_category', sa.String(), nullable=False),
        sa.Column('src_booking_dept_cd', sa.String(), nullable=False),
        sa.Column('src_account_norman_signage', sa.String(), nullable=False),

        sa.Column('src_client_id', sa.String(), nullable=True),
        sa.Column('client_name', sa.String(), nullable=True),
        sa.Column('client_id_type', sa.String(), nullable=True),
        sa.Column('intergorup_identifier', sa.String(), nullable=True),

        sa.Column('acct_func_signage', sa.String(), nullable=False),

        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('src_app_cd', sa.String(), nullable=False),
        sa.Column('src_app_nm', sa.String(), nullable=False),

        sa.Column('default_amount', sa.Numeric(28, 12), nullable=False),
        sa.Column('accounted_amount', sa.Numeric(28, 12), nullable=False),
        sa.Column('fx_rate', sa.Numeric(28, 12), nullable=False),

        sa.Column('src_prev_day_bal_amt', sa.Numeric(28, 12), nullable=False),
        sa.Column('src_crnt_day_debit', sa.Numeric(28, 12), nullable=False),
        sa.Column('src_crnt_day_credit', sa.Numeric(28, 12), nullable=False),
        sa.Column('src_crnt_day_eod_balance', sa.Numeric(28, 12), nullable=False),
        sa.Column('src_back_valued_adjustment', sa.Numeric(28, 12), nullable=False),
        sa.Column('src_measure_trans_amt', sa.Numeric(28, 12), nullable=False),
        sa.Column('src_acct_func_amt', sa.Numeric(28, 12), nullable=False),

        sa.Column('as_of_date', sa.Date(), nullable=False),
        sa.Column('extract_date', sa.Date(), nullable=False),

        schema='interface',
    )


def downgrade() -> None:
    op.drop_table(
        'trial_balance',
        schema='interface',
    )
