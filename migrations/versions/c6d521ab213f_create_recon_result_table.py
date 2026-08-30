"""create recon result table

Revision ID: c6d521ab213f
Revises: 30795b0189f8
Create Date: 2026-08-28 09:42:22.232145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c6d521ab213f'
down_revision: Union[str, Sequence[str], None] = '30795b0189f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS because downgrade() intentionally leaves the recon
    # schema in place (see note there), so a downgrade followed by a
    # re-upgrade must not fail on a schema that already exists.
    op.execute('CREATE SCHEMA IF NOT EXISTS recon')

    op.create_table(
        'result',

        # recon-owned identity/audit
        sa.Column(
            'recon_result_id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            'reconciled_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),

        # Run identity: WORKFLOW_RUN_ID is the source (Interface/GL)
        # workflow being reconciled; PRODUCER_RUN_ID is the recon
        # execution that produced this row.
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

        # Recon grain (RECON_KEYS, minus WORKFLOW_RUN_ID which is above)
        sa.Column('as_of_date', sa.Date(), nullable=False),
        sa.Column('entity_cd', sa.String(), nullable=False),
        sa.Column('branch_cd', sa.String(), nullable=False),
        sa.Column('dept_cd', sa.String(), nullable=False),
        sa.Column('gl_account', sa.String(), nullable=False),
        sa.Column('sub_account', sa.String(), nullable=False),
        sa.Column('affiliate_cd', sa.String(), nullable=False),
        sa.Column('product_cd', sa.String(), nullable=False),
        sa.Column('book_cd', sa.String(), nullable=False),
        sa.Column('source_cd', sa.String(), nullable=False),
        sa.Column('accounted_currency', sa.String(), nullable=False),

        # Balances
        sa.Column('interface_balance', sa.Numeric(28, 12), nullable=False),
        sa.Column('gl_balance', sa.Numeric(28, 12), nullable=False),
        sa.Column('difference_amount', sa.Numeric(28, 12), nullable=False),

        schema='recon',
    )

    # WORKFLOW_RUN_ID is the operational selector for get_results (recon
    # is scoped to a single workflow_run_id in v1), so it is indexed for
    # normal workflow-scoped reads. PRODUCER_RUN_ID remains indexed as
    # exact recon-execution lineage.
    op.create_index(
        'ix_recon_result_workflow_run_id',
        'result',
        ['workflow_run_id'],
        schema='recon',
    )
    op.create_index(
        'ix_recon_result_producer_run_id',
        'result',
        ['producer_run_id'],
        schema='recon',
    )


def downgrade() -> None:
    # The recon schema is expected to hold further recon-owned tables,
    # so only the table this revision created is dropped; the schema
    # itself is left for future recon revisions to manage.
    op.drop_index(
        'ix_recon_result_producer_run_id',
        table_name='result',
        schema='recon',
    )
    op.drop_index(
        'ix_recon_result_workflow_run_id',
        table_name='result',
        schema='recon',
    )
    op.drop_table('result', schema='recon')
