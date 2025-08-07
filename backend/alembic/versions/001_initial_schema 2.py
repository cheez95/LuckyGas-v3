"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (with IF NOT EXISTS handling)
    op.execute("DO $$ BEGIN CREATE TYPE customertype AS ENUM ('commercial', 'residential', 'wholesale'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE invoicestatus AS ENUM ('draft', 'sent', 'paid', 'partial', 'overdue', 'cancelled'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE invoicetype AS ENUM ('standard', 'recurring', 'deposit', 'credit_note'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE invoicepaymentstatus AS ENUM ('pending', 'partial', 'paid', 'overdue'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE paymentmethod AS ENUM ('cash', 'check', 'bank_transfer', 'mobile_payment', 'credit_card'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE deliverystatus AS ENUM ('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE routestatus AS ENUM ('draft', 'scheduled', 'in_progress', 'completed', 'cancelled'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE deliverymethod AS ENUM ('home_delivery', 'factory_direct', 'self_pickup'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_driver', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # Create customers table
    op.create_table('customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('customer_type', postgresql.ENUM('commercial', 'residential', 'wholesale', name='customertype'), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('district', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('postal_code', sa.String(), nullable=True),
        sa.Column('tax_id', sa.String(), nullable=True),
        sa.Column('invoice_title', sa.String(), nullable=True),
        sa.Column('contact_person', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('credit_limit', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('balance', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_customer_code'), 'customers', ['customer_code'], unique=True)
    op.create_index(op.f('ix_customers_email'), 'customers', ['email'], unique=False)
    op.create_index(op.f('ix_customers_phone'), 'customers', ['phone'], unique=False)
    
    # Create gas_products table
    op.create_table('gas_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('size_kg', sa.Float(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('deposit_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deposit_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('delivery_method', postgresql.ENUM('home_delivery', 'factory_direct', 'self_pickup', name='deliverymethod'), nullable=False),
        sa.Column('attributes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gas_products_product_code'), 'gas_products', ['product_code'], unique=True)
    
    # Create vehicles table
    op.create_table('vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('license_plate', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('capacity_kg', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicles_license_plate'), 'vehicles', ['license_plate'], unique=True)


def downgrade() -> None:
    # Drop tables
    op.drop_table('vehicles')
    op.drop_table('gas_products')
    op.drop_table('customers')
    op.drop_table('users')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS deliverymethod")
    op.execute("DROP TYPE IF EXISTS routestatus")
    op.execute("DROP TYPE IF EXISTS deliverystatus")
    op.execute("DROP TYPE IF EXISTS paymentmethod")
    op.execute("DROP TYPE IF EXISTS invoicepaymentstatus")
    op.execute("DROP TYPE IF EXISTS invoicetype")
    op.execute("DROP TYPE IF EXISTS invoicestatus")
    op.execute("DROP TYPE IF EXISTS customertype")