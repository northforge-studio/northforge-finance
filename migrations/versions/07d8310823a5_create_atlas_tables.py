"""create atlas tables

Revision ID: 07d8310823a5
Revises: a1542da54de4
Create Date: 2026-08-25 23:11:44.959186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07d8310823a5'
down_revision: Union[str, Sequence[str], None] = 'a1542da54de4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Column types/nullability mirror atlas/contracts.py's
    # MAPPING_META_SCHEMA / MAPPING_DATA_SCHEMA exactly (all fields are
    # nullable there).
    op.create_table(
        'meta',
        sa.Column('id', sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column('mapping_name', sa.String(), nullable=True),
        sa.Column('mapping_data_name', sa.String(), nullable=True),
        sa.Column('metadata_field_name', sa.String(), nullable=True),
        sa.Column('logical_field_name', sa.String(), nullable=True),
        sa.Column('field_type', sa.String(), nullable=True),
        sa.Column('lookup_type', sa.String(), nullable=True),
        sa.Column('src_field_name', sa.String(), nullable=True),
        sa.Column('datatype', sa.String(), nullable=True),
        sa.Column('ui_field_order', sa.Integer(), nullable=True),
        schema='atlas',
    )

    columns = [
        sa.Column('id', sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column('mapping_name', sa.String(), nullable=True),
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
        sa.Column('weightage', sa.String(), nullable=True)
    )
    columns.append(
        sa.Column('status', sa.String(), nullable=False)
    )

    op.create_table(
        'data',
        *columns,
        schema='atlas',
    )


def downgrade() -> None:
    op.drop_table('data', schema='atlas')
    op.drop_table('meta', schema='atlas')
