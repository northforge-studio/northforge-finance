"""create registry tables

Revision ID: f7d5990e47bc
Revises: 6c2be0b51add
Create Date: 2026-08-25 23:15:09.914975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7d5990e47bc'
down_revision: Union[str, Sequence[str], None] = '6c2be0b51add'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = ['gl_entity', 'gl_dept', 'gl_branch', 'gl_account', 'gl_sub_account',
           'gl_affiliate', 'gl_product', 'gl_book', 'gl_source']


def upgrade() -> None:
    op.create_table(
        'gl_entity',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('ent_cd', sa.String(), nullable=False),
        sa.Column('ent_ds', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'ent_cd', name='uq_gl_entity_business_dt_ent_cd',
        ),
        schema='registry',
    )

    op.create_table(
        'gl_dept',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('dept_cd', sa.String(), nullable=False),
        sa.Column('dept_ds', sa.String(), nullable=False),
        sa.Column('ent_cd', sa.String(), nullable=False),
        sa.Column('bch_cd', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'dept_cd', name='uq_gl_dept_business_dt_dept_cd',
        ),
        schema='registry',
    )

    op.create_table(
        'gl_branch',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('bch_cd', sa.String(), nullable=False),
        sa.Column('bch_ds', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'bch_cd', name='uq_gl_branch_business_dt_bch_cd',
        ),
        schema='registry',
    )

    op.create_table(
        'gl_account',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('acct_cd', sa.String(), nullable=False),
        sa.Column('acct_ds', sa.String(), nullable=False),
        sa.Column('suspns_in', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'acct_cd', name='uq_gl_account_business_dt_acct_cd',
        ),
        schema='registry',
    )

    op.create_table(
        'gl_sub_account',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('sub_acct_cd', sa.String(), nullable=False),
        sa.Column('sub_acct_ds', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'sub_acct_cd',
            name='uq_gl_sub_account_business_dt_sub_acct_cd',
        ),
        schema='registry',
    )

    op.create_table(
        'gl_affiliate',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('affil_cd', sa.String(), nullable=False),
        sa.Column('affil_ds', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'affil_cd',
            name='uq_gl_affiliate_business_dt_affil_cd',
        ),
        schema='registry',
    )

    op.create_table(
        'gl_product',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('prod_cd', sa.String(), nullable=False),
        sa.Column('prod_ds', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'prod_cd', name='uq_gl_product_business_dt_prod_cd',
        ),
        schema='registry',
    )

    op.create_table(
        'gl_book',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('bk_cd', sa.String(), nullable=False),
        sa.Column('bk_ds', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'bk_cd', name='uq_gl_book_business_dt_bk_cd',
        ),
        schema='registry',
    )

    op.create_table(
        'gl_source',
        sa.Column('business_dt', sa.Date(), nullable=False),
        sa.Column('srce_cd', sa.String(), nullable=False),
        sa.Column('srce_ds', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.UniqueConstraint(
            'business_dt', 'srce_cd', name='uq_gl_source_business_dt_srce_cd',
        ),
        schema='registry',
    )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_table(table, schema='registry')
