"""Add delivery history items table

Revision ID: 004
Revises: 003
Create Date: 2025-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create delivery_history_items table
    op.create_table('delivery_history_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('delivery_history_id', sa.Integer(), nullable=False),
        sa.Column('gas_product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('subtotal', sa.Float(), nullable=False),
        sa.Column('is_flow_delivery', sa.Boolean(), nullable=True, default=False),
        sa.Column('flow_quantity', sa.Float(), nullable=True),
        sa.Column('legacy_product_code', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['delivery_history_id'], ['delivery_history.id'], ),
        sa.ForeignKeyConstraint(['gas_product_id'], ['gas_products.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_delivery_history_items_id'), 'delivery_history_items', ['id'], unique=False)


def downgrade() -> None:
    # Drop delivery_history_items table
    op.drop_index(op.f('ix_delivery_history_items_id'), table_name='delivery_history_items')
    op.drop_table('delivery_history_items')