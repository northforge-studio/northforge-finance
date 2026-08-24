"""create reference tables

Revision ID: 3d7b75443ddb
Revises: 992915a00115
Create Date: 2026-08-23 20:07:39.684611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d7b75443ddb'
down_revision: Union[str, Sequence[str], None] = '992915a00115'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'counterparty',
        sa.Column(
            'id',
            sa.Integer(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column('aud_load_id', sa.String(), nullable=False),
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('ver_nb', sa.Integer(), nullable=False),
        sa.Column('cpty_ref_id', sa.String(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=False),
        sa.Column('cpty_nm', sa.String(), nullable=False),
        sa.Column('client_id_type', sa.String(), nullable=False),
        schema='reference',
    )

    op.create_table(
        'fx_rate',
        sa.Column(
            'id',
            sa.Integer(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column('aud_load_id', sa.String(), nullable=False),
        sa.Column('conversion_dt', sa.Date(), nullable=False),
        sa.Column('ver_nb', sa.Integer(), nullable=False),
        sa.Column('from_currency', sa.String(), nullable=False),
        sa.Column('to_currency', sa.String(), nullable=False),
        sa.Column(
            'fx_rate',
            sa.Numeric(28, 12),
            nullable=False,
        ),
        schema='reference',
    )


def downgrade() -> None:
    op.drop_table(
        'fx_rate',
        schema='reference',
    )

    op.drop_table(
        'counterparty',
        schema='reference',
    )
