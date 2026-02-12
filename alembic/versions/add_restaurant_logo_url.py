"""add logo_url to restaurant

Revision ID: b1c2d3e4f5a6
Revises: a672a4af697a
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


revision = 'b1c2d3e4f5a6'
down_revision = 'a672a4af697a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('restaurant', sa.Column('logo_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('restaurant', 'logo_url')
