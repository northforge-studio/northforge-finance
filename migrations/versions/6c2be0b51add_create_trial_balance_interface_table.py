"""create trial balance interface table

Revision ID: 6c2be0b51add
Revises: 3e1ac48afe80
Create Date: 2026-08-25 23:14:38.269208

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6c2be0b51add'
down_revision: Union[str, Sequence[str], None] = '3e1ac48afe80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trial_balance',

        sa.Column(
            'workflow_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.workflow_run.workflow_run_id'),
            nullable=False,
        ),
        sa.Column(
            'producer_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.execution_run.run_id'),
            nullable=False,
        ),

        sa.Column('dataclass', sa.String(), nullable=False),

        sa.Column('transaction_number', sa.String(), nullable=False),
        sa.Column('line_number', sa.String(), nullable=False),

        sa.Column('entity_cd', sa.String(), nullable=False),
        sa.Column('dept_cd', sa.String(), nullable=False),
        sa.Column('branch_cd', sa.String(), nullable=False),
        sa.Column('gl_account', sa.String(), nullable=False),
        sa.Column('sub_account', sa.String(), nullable=False),
        sa.Column('affiliate_cd', sa.String(), nullable=False),
        sa.Column('product_cd', sa.String(), nullable=False),
        sa.Column('book_cd', sa.String(), nullable=False),
        sa.Column('source_cd', sa.String(), nullable=False),

        sa.Column('cr_dr_ind', sa.String(), nullable=False),

        sa.Column('foundry_rule_id', sa.String(), nullable=False),
        sa.Column('posting_id', sa.String(), nullable=False),
        sa.Column('posting_stream', sa.String(), nullable=False),

        sa.Column('src_record_id', sa.String(), nullable=False),
        sa.Column('src_app_cd', sa.String(), nullable=False),

        sa.Column('transaction_currency', sa.String(), nullable=False),
        sa.Column('transaction_amount', sa.Numeric(28, 12), nullable=False),

        sa.Column('accounted_currency', sa.String(), nullable=False),
        sa.Column('accounted_amount', sa.Numeric(28, 12), nullable=False),

        sa.Column('fx_rate', sa.Numeric(28, 12), nullable=False),

        sa.Column('as_of_date', sa.Date(), nullable=False),
        sa.Column('business_date', sa.Date(), nullable=False),

        schema='interface',
    )

    op.create_index(
        'ix_interface_trial_balance_producer_run_id',
        'trial_balance',
        ['producer_run_id'],
        schema='interface',
    )


def downgrade() -> None:
    op.drop_index(
        'ix_interface_trial_balance_producer_run_id',
        table_name='trial_balance',
        schema='interface',
    )
    op.drop_table('trial_balance', schema='interface')
