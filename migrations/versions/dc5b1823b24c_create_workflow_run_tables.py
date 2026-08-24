"""create workflow run tables

Revision ID: dc5b1823b24c
Revises: dd7b22456645
Create Date: 2026-08-24 17:08:24.362368

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'dc5b1823b24c'
down_revision: Union[str, Sequence[str], None] = 'dd7b22456645'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workflow_run',

        sa.Column(
            'workflow_run_id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),

        sa.Column('dataclass', sa.String(), nullable=False),
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('batch_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),

        sa.Column(
            'started_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            'completed_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),

        schema='core',
    )

    op.create_table(
        'execution_run',

        sa.Column(
            'run_id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            'workflow_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.workflow_run.workflow_run_id'),
            nullable=False,
        ),
        sa.Column(
            'parent_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.execution_run.run_id'),
            nullable=True,
        ),

        sa.Column('component', sa.String(), nullable=False),
        sa.Column('operation', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),

        sa.Column(
            'started_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            'completed_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            'retry_of_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.execution_run.run_id'),
            nullable=True,
        ),

        schema='core',
    )


def downgrade() -> None:
    op.drop_table('execution_run', schema='core')
    op.drop_table('workflow_run', schema='core')
