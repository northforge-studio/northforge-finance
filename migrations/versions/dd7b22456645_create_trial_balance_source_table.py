"""create trial balance source table

Revision ID: dd7b22456645
Revises: d85d37100d53
Create Date: 2026-08-24 14:42:52.767010

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd7b22456645'
down_revision: Union[str, Sequence[str], None] = 'd85d37100d53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trial_balance',

        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('extract_dt', sa.Date(), nullable=False),
        sa.Column('as_of_dt', sa.Date(), nullable=False),
        sa.Column('business_dt', sa.Date(), nullable=False),

        sa.Column('src_app_cd', sa.String(), nullable=False),
        sa.Column('src_app_nm', sa.String(), nullable=False),
        sa.Column('src_record_id', sa.String(), nullable=False),

        sa.Column('src_entity_cd', sa.String(), nullable=False),
        sa.Column('src_booking_dept_cd', sa.String(), nullable=False),

        sa.Column('src_account_id', sa.String(), nullable=False),
        sa.Column('src_account_nm', sa.String(), nullable=False),
        sa.Column('src_acct_category', sa.String(), nullable=False),
        sa.Column('src_acct_type', sa.String(), nullable=False),
        sa.Column('norm_acct_sign', sa.String(), nullable=False),

        sa.Column('src_client_id', sa.String(), nullable=True),
        sa.Column('src_client_nm', sa.String(), nullable=True),
        sa.Column('cpty_ref_id', sa.String(), nullable=True),

        sa.Column('src_measure_nm', sa.String(), nullable=False),
        sa.Column('src_measure_ccy_cd', sa.String(), nullable=False),
        sa.Column(
            'src_measure_trans_amt',
            sa.Numeric(28, 12),
            nullable=False,
        ),
        sa.Column(
            'posting_measure_ccy_cd',
            sa.String(),
            nullable=False,
        ),

        schema='foundry_source',
    )


def downgrade() -> None:
    op.drop_table(
        'trial_balance',
        schema='foundry_source',
    )