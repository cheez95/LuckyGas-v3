"""Add performance optimization indexes

Revision ID: performance_indexes_001
Revises: 
Create Date: 2024-01-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'performance_indexes_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add performance optimization indexes for frequently queried columns"""
    
    # Customer table indexes
    op.create_index(
        'ix_customers_phone_number',
        'customers',
        ['phone_number'],
        unique=False
    )
    op.create_index(
        'ix_customers_status_created_at',
        'customers',
        ['status', 'created_at'],
        unique=False
    )
    op.create_index(
        'ix_customers_area',
        'customers',
        ['area'],
        unique=False
    )
    
    # Orders table indexes
    op.create_index(
        'ix_orders_customer_id_created_at',
        'orders',
        ['customer_id', 'created_at'],
        unique=False
    )
    op.create_index(
        'ix_orders_status_delivery_date',
        'orders',
        ['status', 'delivery_date'],
        unique=False
    )
    op.create_index(
        'ix_orders_route_id',
        'orders',
        ['route_id'],
        unique=False
    )
    op.create_index(
        'ix_orders_priority_status',
        'orders',
        ['priority', 'status'],
        unique=False
    )
    
    # Routes table indexes
    op.create_index(
        'ix_routes_status_date',
        'routes',
        ['status', 'date'],
        unique=False
    )
    op.create_index(
        'ix_routes_driver_id_date',
        'routes',
        ['driver_id', 'date'],
        unique=False
    )
    
    # Deliveries table indexes (if exists)
    try:
        op.create_index(
            'ix_deliveries_order_id',
            'deliveries',
            ['order_id'],
            unique=False
        )
        op.create_index(
            'ix_deliveries_route_id_sequence',
            'deliveries',
            ['route_id', 'sequence'],
            unique=False
        )
        op.create_index(
            'ix_deliveries_status_delivered_at',
            'deliveries',
            ['status', 'delivered_at'],
            unique=False
        )
    except Exception:
        pass  # Table might not exist if deliveries are part of orders
    
    # Users table indexes
    op.create_index(
        'ix_users_email',
        'users',
        ['email'],
        unique=True
    )
    op.create_index(
        'ix_users_username',
        'users',
        ['username'],
        unique=True
    )
    op.create_index(
        'ix_users_role_is_active',
        'users',
        ['role', 'is_active'],
        unique=False
    )
    
    # Products table indexes (if exists)
    try:
        op.create_index(
            'ix_products_code',
            'products',
            ['code'],
            unique=True
        )
        op.create_index(
            'ix_products_type_active',
            'products',
            ['type', 'is_active'],
            unique=False
        )
    except Exception:
        pass
    
    # Order items table indexes (if exists)
    try:
        op.create_index(
            'ix_order_items_order_id',
            'order_items',
            ['order_id'],
            unique=False
        )
        op.create_index(
            'ix_order_items_product_id',
            'order_items',
            ['product_id'],
            unique=False
        )
    except Exception:
        pass
    
    # Analytics/reporting indexes for aggregation queries
    try:
        # Create a materialized view for daily order statistics (PostgreSQL specific)
        op.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS daily_order_stats AS
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as total_orders,
                COUNT(DISTINCT customer_id) as unique_customers,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_orders,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_orders,
                AVG(CASE WHEN status = 'completed' 
                    THEN EXTRACT(EPOCH FROM (updated_at - created_at))/3600 
                    ELSE NULL END) as avg_completion_hours
            FROM orders
            GROUP BY DATE(created_at)
            WITH DATA;
            
            CREATE UNIQUE INDEX ON daily_order_stats (date);
        """)
        
        # Create index for refreshing the materialized view
        op.execute("""
            CREATE OR REPLACE FUNCTION refresh_daily_order_stats()
            RETURNS void AS $$
            BEGIN
                REFRESH MATERIALIZED VIEW CONCURRENTLY daily_order_stats;
            END;
            $$ LANGUAGE plpgsql;
        """)
    except Exception:
        pass  # Skip if not PostgreSQL or view already exists
    
    # Add partial indexes for common queries
    try:
        # Index for active customers only
        op.execute("""
            CREATE INDEX ix_customers_active 
            ON customers (id, name) 
            WHERE status = 'active';
        """)
        
        # Index for pending orders
        op.execute("""
            CREATE INDEX ix_orders_pending 
            ON orders (id, customer_id, delivery_date) 
            WHERE status IN ('pending', 'confirmed');
        """)
        
        # Index for today's routes
        op.execute("""
            CREATE INDEX ix_routes_today 
            ON routes (id, driver_id, status) 
            WHERE date = CURRENT_DATE;
        """)
    except Exception:
        pass  # Skip if partial indexes not supported


def downgrade():
    """Remove performance optimization indexes"""
    
    # Drop customer indexes
    op.drop_index('ix_customers_phone_number', 'customers')
    op.drop_index('ix_customers_status_created_at', 'customers')
    op.drop_index('ix_customers_area', 'customers')
    
    # Drop order indexes
    op.drop_index('ix_orders_customer_id_created_at', 'orders')
    op.drop_index('ix_orders_status_delivery_date', 'orders')
    op.drop_index('ix_orders_route_id', 'orders')
    op.drop_index('ix_orders_priority_status', 'orders')
    
    # Drop route indexes
    op.drop_index('ix_routes_status_date', 'routes')
    op.drop_index('ix_routes_driver_id_date', 'routes')
    
    # Drop delivery indexes (if exist)
    try:
        op.drop_index('ix_deliveries_order_id', 'deliveries')
        op.drop_index('ix_deliveries_route_id_sequence', 'deliveries')
        op.drop_index('ix_deliveries_status_delivered_at', 'deliveries')
    except Exception:
        pass
    
    # Drop user indexes
    op.drop_index('ix_users_email', 'users')
    op.drop_index('ix_users_username', 'users')
    op.drop_index('ix_users_role_is_active', 'users')
    
    # Drop product indexes (if exist)
    try:
        op.drop_index('ix_products_code', 'products')
        op.drop_index('ix_products_type_active', 'products')
    except Exception:
        pass
    
    # Drop order item indexes (if exist)
    try:
        op.drop_index('ix_order_items_order_id', 'order_items')
        op.drop_index('ix_order_items_product_id', 'order_items')
    except Exception:
        pass
    
    # Drop materialized view and function
    try:
        op.execute("DROP MATERIALIZED VIEW IF EXISTS daily_order_stats;")
        op.execute("DROP FUNCTION IF EXISTS refresh_daily_order_stats();")
    except Exception:
        pass
    
    # Drop partial indexes
    try:
        op.execute("DROP INDEX IF EXISTS ix_customers_active;")
        op.execute("DROP INDEX IF EXISTS ix_orders_pending;")
        op.execute("DROP INDEX IF EXISTS ix_routes_today;")
    except Exception:
        pass