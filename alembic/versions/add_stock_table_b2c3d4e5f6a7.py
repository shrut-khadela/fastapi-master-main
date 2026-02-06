"""add stock table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock",
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit_of_measure", sa.String(), nullable=True),
        sa.Column("reorder_level", sa.Float(), nullable=True),
        sa.Column("cost_price", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(op.f("ix_stock_name"), "stock", ["name"], unique=False)
    op.create_index(op.f("ix_stock_quantity"), "stock", ["quantity"], unique=False)
    op.create_index(op.f("ix_stock_unit_of_measure"), "stock", ["unit_of_measure"], unique=False)
    op.create_index(op.f("ix_stock_reorder_level"), "stock", ["reorder_level"], unique=False)
    op.create_index(op.f("ix_stock_cost_price"), "stock", ["cost_price"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_cost_price"), table_name="stock")
    op.drop_index(op.f("ix_stock_reorder_level"), table_name="stock")
    op.drop_index(op.f("ix_stock_unit_of_measure"), table_name="stock")
    op.drop_index(op.f("ix_stock_quantity"), table_name="stock")
    op.drop_index(op.f("ix_stock_name"), table_name="stock")
    op.drop_table("stock")
