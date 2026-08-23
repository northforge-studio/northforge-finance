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
    op.execute('CREATE SCHEMA foundry_config')
    op.execute('CREATE SCHEMA foundry_source')
    op.execute('CREATE SCHEMA foundry_staging')
    op.execute('CREATE SCHEMA foundry_enrichment')
    op.execute('CREATE SCHEMA foundry_reporting')
    op.execute('CREATE SCHEMA foundry_posting')

    op.execute('CREATE SCHEMA atlas')
    op.execute('CREATE SCHEMA reference')
    op.execute('CREATE SCHEMA core')


def downgrade() -> None:
    op.execute('DROP SCHEMA core')
    op.execute('DROP SCHEMA reference')
    op.execute('DROP SCHEMA atlas')

    op.execute('DROP SCHEMA foundry_posting')
    op.execute('DROP SCHEMA foundry_reporting')
    op.execute('DROP SCHEMA foundry_enrichment')
    op.execute('DROP SCHEMA foundry_staging')
    op.execute('DROP SCHEMA foundry_source')
    op.execute('DROP SCHEMA foundry_config')
