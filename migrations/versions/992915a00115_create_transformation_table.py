"""create transformation table

Revision ID: 992915a00115
Revises: 7c030d7ac6f3
Create Date: 2026-08-23 17:59:58.039132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '992915a00115'
down_revision: Union[str, Sequence[str], None] = '7c030d7ac6f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transformation',

        sa.Column(
            'id',
            sa.Integer(),
            sa.Identity(),
            primary_key=True,
        ),

        sa.Column('src_app_cd', sa.String(), nullable=False),
        sa.Column('dataclass', sa.String(), nullable=False),
        sa.Column('output_col_name', sa.String(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),

        sa.Column('zone', sa.String(), nullable=False),
        sa.Column('stage', sa.String(), nullable=False),
        sa.Column('sub_stage', sa.String(), nullable=True),

        sa.Column('expression', sa.Text(), nullable=False),
        sa.Column('status', sa.String(1), nullable=False),

        schema='foundry_config',
    )


def downgrade() -> None:
    op.drop_table(
        'transformation',
        schema='foundry_config',
    )
