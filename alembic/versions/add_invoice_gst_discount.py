"""add gst_percent and discount_percent to invoice

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('invoice', sa.Column('gst_percent', sa.Float(), nullable=False, server_default='0'))
    op.add_column('invoice', sa.Column('discount_percent', sa.Float(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('invoice', 'discount_percent')
    op.drop_column('invoice', 'gst_percent')
