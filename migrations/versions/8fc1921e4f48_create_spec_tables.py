"""create spec tables

Revision ID: 8fc1921e4f48
Revises: 08afc5e5ae85
Create Date: 2026-08-25 23:11:22.952063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fc1921e4f48'
down_revision: Union[str, Sequence[str], None] = '08afc5e5ae85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transformation',
        sa.Column('src_app_cd', sa.String(), nullable=False),
        sa.Column('dataclass', sa.String(), nullable=False),
        sa.Column('output_col_name', sa.String(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('zone', sa.String(), nullable=False),
        sa.Column('stage', sa.String(), nullable=False),
        sa.Column('sub_stage', sa.String(), nullable=True),
        sa.Column('expression', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        schema='spec',
    )

    op.create_table(
        'file_layout',
        sa.Column('src_app_cd', sa.String(), nullable=False),
        sa.Column('dataclass', sa.String(), nullable=False),
        sa.Column('posting_attribute_name', sa.String(), nullable=False),
        sa.Column('gl_attribute_name', sa.String(), nullable=False),
        sa.Column('expression', sa.String(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        schema='spec',
    )


def downgrade() -> None:
    op.drop_table('file_layout', schema='spec')
    op.drop_table('transformation', schema='spec')
