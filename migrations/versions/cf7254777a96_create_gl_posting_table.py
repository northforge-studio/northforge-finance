"""create gl posting table

Revision ID: cf7254777a96
Revises: 1685d51261ec
Create Date: 2026-08-26 20:25:21.103243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cf7254777a96'
down_revision: Union[str, Sequence[str], None] = '1685d51261ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'posting',

        # GL-owned identity/audit
        sa.Column(
            'gl_posting_id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            'posted_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),

        # Foundry / business lineage
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

        # Final GL segments (resolved/defaulted values GL actually posted)
        sa.Column('entity_cd', sa.String(), nullable=False),
        sa.Column('branch_cd', sa.String(), nullable=False),
        sa.Column('dept_cd', sa.String(), nullable=False),
        sa.Column('gl_account', sa.String(), nullable=False),
        sa.Column('sub_account', sa.String(), nullable=False),
        sa.Column('affiliate_cd', sa.String(), nullable=False),
        sa.Column('product_cd', sa.String(), nullable=False),
        sa.Column('book_cd', sa.String(), nullable=False),
        sa.Column('source_cd', sa.String(), nullable=False),

        # Accounting
        sa.Column('cr_dr_ind', sa.String(), nullable=False),

        sa.Column('transaction_currency', sa.String(), nullable=False),
        sa.Column('transaction_amount', sa.Numeric(28, 12), nullable=False),

        sa.Column('accounted_currency', sa.String(), nullable=False),
        sa.Column('accounted_amount', sa.Numeric(28, 12), nullable=False),

        sa.Column('fx_rate', sa.Numeric(28, 12), nullable=False),

        sa.Column('as_of_date', sa.Date(), nullable=False),
        sa.Column('business_date', sa.Date(), nullable=False),

        schema='gl',
    )

    op.create_index(
        'ix_gl_posting_business_date',
        'posting',
        ['business_date'],
        schema='gl',
    )

    # WORKFLOW_RUN_ID is the operational selector for get_postings /
    # delete_postings (V1: one producer execution per workflow), since the
    # same business_date can be processed by multiple GL workflows.
    # PRODUCER_RUN_ID remains indexed as exact producer lineage.
    op.create_index(
        'ix_gl_posting_producer_run_id',
        'posting',
        ['producer_run_id'],
        schema='gl',
    )

    # posting_id is deliberately not unique: more than one gl.posting row
    # may reference the same Foundry POSTING_ID (e.g. future deliberate
    # duplicate-posting scenarios). The index only speeds up the
    # Interface POSTING_ID -> gl.posting POSTING_ID reconciliation trace.
    op.create_index(
        'ix_gl_posting_posting_id',
        'posting',
        ['posting_id'],
        schema='gl',
    )


def downgrade() -> None:
    op.drop_index(
        'ix_gl_posting_posting_id',
        table_name='posting',
        schema='gl',
    )
    op.drop_index(
        'ix_gl_posting_producer_run_id',
        table_name='posting',
        schema='gl',
    )
    op.drop_index(
        'ix_gl_posting_business_date',
        table_name='posting',
        schema='gl',
    )
    op.drop_table('posting', schema='gl')
