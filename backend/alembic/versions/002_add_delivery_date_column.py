"""Add delivery_date column to orders table

Revision ID: 002_add_delivery_date
Revises: 001_simplified_schema
Create Date: 2025-08-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_delivery_date'
down_revision = '001_simplified_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Add delivery_date column to orders table if it doesn't exist
    op.add_column('orders', sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove delivery_date column from orders table
    op.drop_column('orders', 'delivery_date')