"""create registry reference tables

Revision ID: 0401a17ee2e3
Revises: 3aa94a058963
Create Date: 2026-08-25 19:38:33.110144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0401a17ee2e3'
down_revision: Union[str, Sequence[str], None] = '3aa94a058963'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA registry')

    # 1. Entity
    op.create_table(
        'gl_entity',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('ent_cd', sa.String(), nullable=True),
        sa.Column('ent_ds', sa.String(), nullable=True),
        sa.Column('sun_id', sa.String(), nullable=True),
        sa.Column('parent_ent_1_cd', sa.String(), nullable=True),
        sa.Column('parent_ent_2_cd', sa.String(), nullable=True),
        sa.Column('parent_ent_2_nm', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )

    # 2. Department
    op.create_table(
        'gl_dept',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('dept_cd', sa.String(), nullable=True),
        sa.Column('dept_ds', sa.String(), nullable=True),
        sa.Column('lgcy_dept_cd', sa.String(), nullable=True),
        sa.Column('parnt_dept_cd', sa.String(), nullable=True),
        sa.Column('parnt_dept_ds', sa.String(), nullable=True),
        sa.Column('ent_cd', sa.String(), nullable=True),
        sa.Column('ent_nm', sa.String(), nullable=True),
        sa.Column('bch_cd', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )

    # 3. Branch
    op.create_table(
        'gl_branch',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('bch_cd', sa.String(), nullable=True),
        sa.Column('bch_ds', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )

    # 4. Account
    op.create_table(
        'gl_account',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('acct_cd', sa.String(), nullable=True),
        sa.Column('acct_ds', sa.String(), nullable=True),
        sa.Column('parnt_acct_cd', sa.String(), nullable=True),
        sa.Column('parnt_acct_nm', sa.String(), nullable=True),
        sa.Column('suspns_in', sa.String(), nullable=True),
        sa.Column('ig_in', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )

    # 5. Sub-account
    op.create_table(
        'gl_sub_account',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('sub_acct_cd', sa.String(), nullable=True),
        sa.Column('sub_acct_ds', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )

    # 6. Affiliate
    op.create_table(
        'gl_affiliate',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('affil_cd', sa.String(), nullable=True),
        sa.Column('affil_ds', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )

    # 7. Product
    op.create_table(
        'gl_product',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('prod_cd', sa.String(), nullable=True),
        sa.Column('prod_ds', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )

    # 8. Book
    op.create_table(
        'gl_book',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('bk_cd', sa.String(), nullable=True),
        sa.Column('bk_ds', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )

    # 9. Source
    op.create_table(
        'gl_source',
        sa.Column('aud_load_id', sa.String(), nullable=True),
        sa.Column('business_dt', sa.Date(), nullable=True),
        sa.Column('ver_nb', sa.Integer(), nullable=True),
        sa.Column('srce_cd', sa.String(), nullable=True),
        sa.Column('srce_ds', sa.String(), nullable=True),
        sa.Column('rgn_cd', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        schema='registry',
    )


def downgrade() -> None:
    op.drop_table('gl_source', schema='registry')
    op.drop_table('gl_book', schema='registry')
    op.drop_table('gl_product', schema='registry')
    op.drop_table('gl_affiliate', schema='registry')
    op.drop_table('gl_sub_account', schema='registry')
    op.drop_table('gl_account', schema='registry')
    op.drop_table('gl_branch', schema='registry')
    op.drop_table('gl_dept', schema='registry')
    op.drop_table('gl_entity', schema='registry')

    op.execute('DROP SCHEMA registry')
