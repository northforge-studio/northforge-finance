"""create atlas tables

Revision ID: d85d37100d53
Revises: 3d7b75443ddb
Create Date: 2026-08-24 13:04:11.216035

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd85d37100d53'
down_revision: Union[str, Sequence[str], None] = '3d7b75443ddb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'meta',
        sa.Column('id', sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column('aud_load_id', sa.BigInteger(), nullable=False),
        sa.Column('rcd_dt', sa.Date(), nullable=False),
        sa.Column('ver_nb', sa.Integer(), nullable=False),
        sa.Column('eff_start_date', sa.Date(), nullable=False),
        sa.Column('eff_end_date', sa.Date(), nullable=False),
        sa.Column('mapping_category', sa.String(), nullable=False),
        sa.Column('mapping_name', sa.String(), nullable=False),
        sa.Column('mapping_data_name', sa.String(), nullable=False),
        sa.Column('metadata_field_name', sa.String(), nullable=False),
        sa.Column('logical_field_name', sa.String(), nullable=False),
        sa.Column('field_type', sa.String(), nullable=False),
        sa.Column('lookup_type', sa.String(), nullable=True),
        sa.Column('datatype', sa.String(), nullable=False),
        sa.Column('src_field_name', sa.String(), nullable=True),
        sa.Column('ui_field_visibility', sa.String(), nullable=False),
        sa.Column('control', sa.String(), nullable=True),
        sa.Column('ui_field_order', sa.Integer(), nullable=False),
        schema='atlas',
    )

    columns = [
        sa.Column('id', sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column('aud_load_id', sa.BigInteger(), nullable=False),
        sa.Column('rcd_dt', sa.Date(), nullable=False),
        sa.Column('ver_nb', sa.Integer(), nullable=False),
        sa.Column('eff_start_date', sa.Date(), nullable=False),
        sa.Column('eff_end_date', sa.Date(), nullable=False),
        sa.Column('mdm_id', sa.BigInteger(), nullable=False),
        sa.Column('mapping_category', sa.String(), nullable=False),
        sa.Column('mapping_name', sa.String(), nullable=False),
        sa.Column('mapping_data_name', sa.String(), nullable=False),
    ]

    columns.extend(
        sa.Column(f'input_col{i}', sa.String(), nullable=True)
        for i in range(1, 21)
    )

    columns.extend(
        sa.Column(f'output_col{i}', sa.String(), nullable=True)
        for i in range(1, 21)
    )

    columns.append(
        sa.Column('weightage', sa.String(), nullable=False)
    )

    op.create_table(
        'data',
        *columns,
        schema='atlas',
    )


def downgrade() -> None:
    op.drop_table('data', schema='atlas')
    op.drop_table('meta', schema='atlas')
