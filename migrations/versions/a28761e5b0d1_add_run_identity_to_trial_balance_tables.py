"""add run identity to trial balance tables

Revision ID: a28761e5b0d1
Revises: ad2fef0348c1
Create Date: 2026-08-24 19:08:42.393206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a28761e5b0d1'
down_revision: Union[str, Sequence[str], None] = 'ad2fef0348c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ZONE_SCHEMAS = (
    'foundry_staging',
    'foundry_enrichment',
    'foundry_reporting',
    'foundry_posting',
)


def upgrade() -> None:
    for schema in ZONE_SCHEMAS:
        op.add_column(
            'trial_balance',
            sa.Column(
                'workflow_run_id',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('core.workflow_run.workflow_run_id'),
                nullable=False,
            ),
            schema=schema,
        )
        op.add_column(
            'trial_balance',
            sa.Column(
                'producer_run_id',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('core.execution_run.run_id'),
                nullable=False,
            ),
            schema=schema,
        )


def downgrade() -> None:
    for schema in ZONE_SCHEMAS:
        op.drop_column('trial_balance', 'producer_run_id', schema=schema)
        op.drop_column('trial_balance', 'workflow_run_id', schema=schema)
