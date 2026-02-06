"""add restaurant tables

Revision ID: a1b2c3d4e5f6
Revises: 0d716b5aa63b
Create Date: 2026-01-27 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '0d716b5aa63b'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create the 'menu' table FIRST
    op.create_table('menu',
        sa.Column('item_list', sa.String(), nullable=True),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('category_name', sa.String(), nullable=True),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )
    # Create indexes for menu
    op.create_index(op.f('ix_menu_item_list'), 'menu', ['item_list'], unique=False)
    op.create_index(op.f('ix_menu_price'), 'menu', ['price'], unique=False)
    op.create_index(op.f('ix_menu_quantity'), 'menu', ['quantity'], unique=False)
    op.create_index(op.f('ix_menu_category_name'), 'menu', ['category_name'], unique=False)

    # 2. NOW add the constraint (Because 'menu' exists now)
    op.create_unique_constraint("uq_menu_category_name", "menu", ["category_name"])

    # 3. Create 'menu_item' table (Which relies on the constraint above)
    op.create_table('menu_item',
        sa.Column('item_name', sa.String(), nullable=True),
        sa.Column('item_price', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        # This FK works now because uq_menu_category_name exists!
        sa.ForeignKeyConstraint(['category'], ['menu.category_name'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_menu_item_item_name'), 'menu_item', ['item_name'], unique=False)
    op.create_index(op.f('ix_menu_item_item_price'), 'menu_item', ['item_price'], unique=False)
    op.create_index(op.f('ix_menu_item_category'), 'menu_item', ['category'], unique=False)

    # ... (Rest of your tables: 'table', 'order' remain the same) ...
    # Create table table
    op.create_table('table',
        sa.Column('table_no', sa.Integer(), nullable=True),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_table_table_no'), 'table', ['table_no'], unique=False)

    # Create order table
    op.create_table('order',
        sa.Column('order_list', sa.String(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('order_pending', sa.String(), nullable=True),
        sa.Column('order_done', sa.String(), nullable=True),
        sa.Column('order_cancel', sa.String(), nullable=True),
        sa.Column('table_no', sa.Integer(), nullable=True),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id')
    )
    op.create_index(op.f('ix_order_order_list'), 'order', ['order_list'], unique=False)
    op.create_index(op.f('ix_order_quantity'), 'order', ['quantity'], unique=False)
    op.create_index(op.f('ix_order_table_no'), 'order', ['table_no'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_order_table_no'), table_name='order')
    op.drop_index(op.f('ix_order_quantity'), table_name='order')
    op.drop_index(op.f('ix_order_order_list'), table_name='order')
    op.drop_table('order')
    op.drop_index(op.f('ix_table_table_no'), table_name='table')
    op.drop_table('table')
    op.drop_index(op.f('ix_menu_item_category'), table_name='menu_item')
    op.drop_index(op.f('ix_menu_item_item_price'), table_name='menu_item')
    op.drop_index(op.f('ix_menu_item_item_name'), table_name='menu_item')
    op.drop_table('menu_item')
    op.drop_index(op.f('ix_menu_category_name'), table_name='menu')
    op.drop_index(op.f('ix_menu_quantity'), table_name='menu')
    op.drop_index(op.f('ix_menu_price'), table_name='menu')
    op.drop_index(op.f('ix_menu_item_list'), table_name='menu')
    op.drop_table('menu')
