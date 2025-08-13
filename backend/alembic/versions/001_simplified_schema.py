"""
Create simplified schema with proper indexes
Revision ID: 001_simplified
Create Date: 2024-01-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = '001_simplified'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Create simplified schema with only essential tables and proper indexes
    """
    
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'manager', 'staff', 'driver', 'customer', name='userrole'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])
    
    # Create customers table
    op.create_table('customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('area', sa.String(100), nullable=True),
        sa.Column('customer_type', sa.Enum('residential', 'restaurant', 'commercial', 'industrial', name='customertype'), nullable=True),
        sa.Column('pricing_tier', sa.String(50), nullable=True, default='standard'),
        sa.Column('credit_limit', sa.Float(), nullable=True, default=0.0),
        sa.Column('current_balance', sa.Float(), nullable=True, default=0.0),
        sa.Column('preferred_delivery_time', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_customers_code', 'customers', ['code'], unique=True)
    op.create_index('ix_customers_name', 'customers', ['name'])
    op.create_index('idx_customer_type_active', 'customers', ['customer_type', 'is_active'])
    op.create_index('idx_customer_area', 'customers', ['area'])
    
    # Create products table
    op.create_table('products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('product_type', sa.Enum('gas_50kg', 'gas_20kg', 'gas_16kg', 'gas_10kg', 'gas_4kg', 'accessory', name='producttype'), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('current_stock', sa.Integer(), nullable=True, default=0),
        sa.Column('min_stock_level', sa.Integer(), nullable=True, default=10),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_products_code', 'products', ['code'], unique=True)
    op.create_index('ix_products_product_type', 'products', ['product_type'])
    op.create_index('ix_products_is_active', 'products', ['is_active'])
    
    # Create orders table
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_number', sa.String(50), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('delivery_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'confirmed', 'processing', 'delivered', 'cancelled', name='orderstatus'), nullable=True),
        sa.Column('subtotal', sa.Float(), nullable=True, default=0.0),
        sa.Column('tax', sa.Float(), nullable=True, default=0.0),
        sa.Column('total_amount', sa.Float(), nullable=True, default=0.0),
        sa.Column('paid_amount', sa.Float(), nullable=True, default=0.0),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_orders_order_number', 'orders', ['order_number'], unique=True)
    op.create_index('ix_orders_customer_id', 'orders', ['customer_id'])
    op.create_index('ix_orders_order_date', 'orders', ['order_date'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_delivery_date', 'orders', ['delivery_date'])
    
    # CRITICAL INDEXES FOR PERFORMANCE
    op.create_index('idx_order_customer_date', 'orders', ['customer_id', 'order_date'])
    op.create_index('idx_order_status_date', 'orders', ['status', 'order_date'])
    
    # Create partial index for active orders (PostgreSQL only)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_active_orders 
        ON orders(status) 
        WHERE status IN ('pending', 'confirmed', 'processing')
    """)
    
    # Create order_items table
    op.create_table('order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('total_price', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('ix_order_items_product_id', 'order_items', ['product_id'])
    
    # Create drivers table
    op.create_table('drivers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('driver_code', sa.String(50), nullable=False),
        sa.Column('license_number', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(50), nullable=False),
        sa.Column('max_daily_deliveries', sa.Integer(), nullable=True, default=30),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_available', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_drivers_user_id', 'drivers', ['user_id'], unique=True)
    op.create_index('ix_drivers_driver_code', 'drivers', ['driver_code'], unique=True)
    op.create_index('ix_drivers_license_number', 'drivers', ['license_number'], unique=True)
    op.create_index('ix_drivers_is_active', 'drivers', ['is_active'])
    op.create_index('ix_drivers_is_available', 'drivers', ['is_available'])
    
    # Create vehicles table
    op.create_table('vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('license_plate', sa.String(50), nullable=False),
        sa.Column('vehicle_type', sa.String(50), nullable=True),
        sa.Column('capacity_kg', sa.Float(), nullable=True),
        sa.Column('last_maintenance', sa.Date(), nullable=True),
        sa.Column('next_maintenance', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vehicles_driver_id', 'vehicles', ['driver_id'])
    op.create_index('ix_vehicles_license_plate', 'vehicles', ['license_plate'], unique=True)
    op.create_index('ix_vehicles_is_active', 'vehicles', ['is_active'])
    
    # Create deliveries table - MOST IMPORTANT FOR PERFORMANCE!
    op.create_table('deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=False),  # Denormalized for performance
        sa.Column('delivery_date', sa.Date(), nullable=False),
        sa.Column('scheduled_time', sa.String(50), nullable=True),
        sa.Column('actual_delivery_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('scheduled', 'in_route', 'delivered', 'failed', name='deliverystatus'), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('signature_name', sa.String(255), nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('delivery_notes', sa.Text(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_deliveries_order_id', 'deliveries', ['order_id'], unique=True)
    op.create_index('ix_deliveries_driver_id', 'deliveries', ['driver_id'])
    op.create_index('ix_deliveries_customer_id', 'deliveries', ['customer_id'])
    op.create_index('ix_deliveries_delivery_date', 'deliveries', ['delivery_date'])
    op.create_index('ix_deliveries_status', 'deliveries', ['status'])
    
    # CRITICAL PERFORMANCE INDEXES FOR DELIVERIES
    op.create_index('idx_delivery_customer_date', 'deliveries', ['customer_id', 'delivery_date'])
    op.create_index('idx_delivery_driver_date', 'deliveries', ['driver_id', 'delivery_date'])
    op.create_index('idx_delivery_status_date', 'deliveries', ['status', 'delivery_date'])
    
    # Create partial index for today's deliveries (PostgreSQL only)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_todays_deliveries 
        ON deliveries(delivery_date) 
        WHERE delivery_date >= CURRENT_DATE
    """)
    
    # Create delivery_archive table for old data (>6 months)
    op.create_table('delivery_archive',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_delivery_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('delivery_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('delivery_notes', sa.Text(), nullable=True),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    # Minimal indexes for archive table
    op.create_index('idx_archive_customer_date', 'delivery_archive', ['customer_id', 'delivery_date'])
    op.create_index('idx_archive_date', 'delivery_archive', ['delivery_date'])


def downgrade():
    """Drop all tables"""
    op.drop_table('delivery_archive')
    op.drop_table('deliveries')
    op.drop_table('vehicles')
    op.drop_table('drivers')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_table('customers')
    op.drop_table('users')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS customertype")
    op.execute("DROP TYPE IF EXISTS producttype")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS deliverystatus")