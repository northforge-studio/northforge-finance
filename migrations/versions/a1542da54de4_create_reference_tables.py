"""create reference tables

Revision ID: a1542da54de4
Revises: 8fc1921e4f48
Create Date: 2026-08-25 23:11:33.596781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1542da54de4'
down_revision: Union[str, Sequence[str], None] = '8fc1921e4f48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fx_rate',
        sa.Column('conversion_dt', sa.Date(), nullable=False),
        sa.Column('from_currency', sa.String(), nullable=False),
        sa.Column('to_currency', sa.String(), nullable=False),
        sa.Column('fx_rate', sa.Numeric(28, 12), nullable=False),
        sa.UniqueConstraint(
            'conversion_dt', 'from_currency', 'to_currency',
            name='uq_fx_rate_conversion_dt_from_to',
        ),
        schema='reference',
    )

    op.create_table(
        'counterparty',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('cpty_ref_id', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('cpty_nm', sa.String(), nullable=False),
        sa.Column('client_id_type', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'cpty_ref_id',
            name='uq_counterparty_business_dt_cpty_ref_id',
        ),
        schema='reference',
    )


def downgrade() -> None:
    op.drop_table('counterparty', schema='reference')
    op.drop_table('fx_rate', schema='reference')
