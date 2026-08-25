"""create file layout table

Revision ID: 0d32fb2bf1ef
Revises: a28761e5b0d1
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d32fb2bf1ef'
down_revision: Union[str, Sequence[str], None] = 'a28761e5b0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'file_layout',

        sa.Column(
            'id',
            sa.Integer(),
            sa.Identity(),
            primary_key=True,
        ),

        sa.Column('src_app_cd', sa.String(), nullable=False),
        sa.Column('dataclass', sa.String(), nullable=False),
        sa.Column('posting_attribute_name', sa.String(), nullable=False),
        sa.Column('gl_attribute_name', sa.String(), nullable=False),
        sa.Column('expression', sa.String(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        
        schema='spec',
    )


def downgrade() -> None:
    op.drop_table(
        'file_layout',
        schema='spec',
    )
