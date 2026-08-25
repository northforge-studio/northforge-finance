"""create gl_ingest schema

Revision ID: 3dc8643ac334
Revises: 0d32fb2bf1ef
Create Date: 2026-08-25 13:25:00.844183

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3dc8643ac334'
down_revision: Union[str, Sequence[str], None] = '0d32fb2bf1ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA interface')


def downgrade() -> None:
    op.execute('DROP SCHEMA interface')
