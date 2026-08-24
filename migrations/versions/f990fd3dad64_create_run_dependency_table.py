"""create run dependency table

Revision ID: f990fd3dad64
Revises: dc5b1823b24c
Create Date: 2026-08-24 17:37:45.950041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f990fd3dad64'
down_revision: Union[str, Sequence[str], None] = 'dc5b1823b24c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'run_dependency',

        sa.Column(
            'consumer_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.execution_run.run_id'),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            'producer_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.execution_run.run_id'),
            primary_key=True,
            nullable=False,
        ),
        sa.Column('input_role', sa.String(), nullable=True),

        schema='core',
    )


def downgrade() -> None:
    op.drop_table('run_dependency', schema='core')
