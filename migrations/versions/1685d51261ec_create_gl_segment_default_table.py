"""create gl segment default table

Revision ID: 1685d51261ec
Revises: f7d5990e47bc
Create Date: 2026-08-26 17:23:11.150612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1685d51261ec'
down_revision: Union[str, Sequence[str], None] = 'f7d5990e47bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS because downgrade() intentionally leaves the gl
    # schema in place (see note there), so a downgrade followed by a
    # re-upgrade must not fail on a schema that already exists.
    op.execute('CREATE SCHEMA IF NOT EXISTS gl')

    op.create_table(
        'segment_default',
        sa.Column('segment_type', sa.String(), nullable=False),
        sa.Column('context_type', sa.String(), nullable=False),
        sa.Column('context_value', sa.String(), nullable=False),
        sa.Column('default_value', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'segment_type', 'context_type', 'context_value',
            name='uq_segment_default_segment_type_context_type_context_value',
        ),
        schema='gl',
    )


def downgrade() -> None:
    # The gl schema is expected to hold further GL-owned tables, so only
    # the table this revision created is dropped; the schema itself is
    # left for future gl revisions to manage.
    op.drop_table('segment_default', schema='gl')
