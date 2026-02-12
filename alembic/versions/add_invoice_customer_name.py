"""add customer_name to invoice

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-02-11

"""
from alembic import op
import sqlalchemy as sa


revision = 'e4f5a6b7c8d9'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('invoice', sa.Column('customer_name', sa.String(length=255), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('invoice', 'customer_name')
