"""create trial balance source table

Revision ID: e1ce1c36ac40
Revises: 07d8310823a5
Create Date: 2026-08-25 23:12:03.990176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1ce1c36ac40'
down_revision: Union[str, Sequence[str], None] = '07d8310823a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trial_balance',
        sa.Column('as_of_dt', sa.Date(), nullable=False),
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('src_app_cd', sa.String(), nullable=False),
        sa.Column('src_record_id', sa.String(), nullable=False),
        sa.Column('src_entity_cd', sa.String(), nullable=False),
        sa.Column('src_booking_dept_cd', sa.String(), nullable=False),
        sa.Column('src_account_id', sa.String(), nullable=False),
        sa.Column('src_acct_type', sa.String(), nullable=False),
        sa.Column('src_client_id', sa.String(), nullable=False),
        sa.Column('cpty_ref_id', sa.String(), nullable=False),
        sa.Column('src_measure_nm', sa.String(), nullable=False),
        sa.Column('src_measure_ccy_cd', sa.String(), nullable=False),
        sa.Column('src_measure_trans_amt', sa.Numeric(28, 12), nullable=False),
        sa.Column('posting_measure_ccy_cd', sa.String(), nullable=False),
        schema='foundry_source',
    )

    op.create_index(
        'ix_foundry_source_trial_balance_business_dt',
        'trial_balance',
        ['business_dt'],
        schema='foundry_source',
    )
    op.create_index(
        'ix_foundry_source_trial_balance_business_dt_src_record_id',
        'trial_balance',
        ['business_dt', 'src_record_id'],
        schema='foundry_source',
    )


def downgrade() -> None:
    op.drop_index(
        'ix_foundry_source_trial_balance_business_dt_src_record_id',
        table_name='trial_balance',
        schema='foundry_source',
    )
    op.drop_index(
        'ix_foundry_source_trial_balance_business_dt',
        table_name='trial_balance',
        schema='foundry_source',
    )
    op.drop_table('trial_balance', schema='foundry_source')
