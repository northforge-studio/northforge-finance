"""create gl rejection table

Revision ID: 30795b0189f8
Revises: cf7254777a96
Create Date: 2026-08-26 20:44:48.375148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '30795b0189f8'
down_revision: Union[str, Sequence[str], None] = 'cf7254777a96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rejection',

        # GL-owned identity/audit
        sa.Column(
            'gl_rejection_id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            'rejected_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),

        # Foundry / business lineage (enough to trace back to Interface)
        sa.Column(
            'workflow_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.workflow_run.workflow_run_id'),
            nullable=False,
        ),
        sa.Column(
            'producer_run_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('core.execution_run.run_id'),
            nullable=False,
        ),

        sa.Column('dataclass', sa.String(), nullable=False),

        sa.Column('transaction_number', sa.String(), nullable=False),
        sa.Column('line_number', sa.String(), nullable=False),

        sa.Column('foundry_rule_id', sa.String(), nullable=False),
        sa.Column('posting_id', sa.String(), nullable=False),
        sa.Column('posting_stream', sa.String(), nullable=False),

        sa.Column('src_record_id', sa.String(), nullable=False),
        sa.Column('src_app_cd', sa.String(), nullable=False),

        sa.Column('business_date', sa.Date(), nullable=False),
        sa.Column('as_of_date', sa.Date(), nullable=False),

        # Rejection diagnostics
        sa.Column('rejection_type', sa.String(), nullable=False),
        sa.Column('rejection_detail', sa.String(), nullable=False),

        schema='gl',
    )

    op.create_index(
        'ix_gl_rejection_business_date',
        'rejection',
        ['business_date'],
        schema='gl',
    )

    # WORKFLOW_RUN_ID is the operational selector for get_rejections /
    # delete_rejections (V1: one producer execution per workflow), since
    # the same business_date can be processed by multiple GL workflows.
    # PRODUCER_RUN_ID remains indexed as exact producer lineage.
    op.create_index(
        'ix_gl_rejection_producer_run_id',
        'rejection',
        ['producer_run_id'],
        schema='gl',
    )


def downgrade() -> None:
    op.drop_index(
        'ix_gl_rejection_producer_run_id',
        table_name='rejection',
        schema='gl',
    )
    op.drop_index(
        'ix_gl_rejection_business_date',
        table_name='rejection',
        schema='gl',
    )
    op.drop_table('rejection', schema='gl')
