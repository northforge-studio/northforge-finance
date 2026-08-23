"""create initial schema

Revision ID: 7c030d7ac6f3
Revises: 
Create Date: 2026-08-23 15:41:22.803678

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7c030d7ac6f3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA adi_config')
    op.execute('CREATE SCHEMA adi_source')
    op.execute('CREATE SCHEMA adi_staging')
    op.execute('CREATE SCHEMA adi_enrichment')
    op.execute('CREATE SCHEMA adi_reporting')
    op.execute('CREATE SCHEMA adi_posting')

    op.execute('CREATE SCHEMA finmap')
    op.execute('CREATE SCHEMA reference')
    op.execute('CREATE SCHEMA core')


def downgrade() -> None:
    op.execute('DROP SCHEMA core')
    op.execute('DROP SCHEMA reference')
    op.execute('DROP SCHEMA finmap')

    op.execute('DROP SCHEMA adi_posting')
    op.execute('DROP SCHEMA adi_reporting')
    op.execute('DROP SCHEMA adi_enrichment')
    op.execute('DROP SCHEMA adi_staging')
    op.execute('DROP SCHEMA adi_source')
    op.execute('DROP SCHEMA adi_config')
