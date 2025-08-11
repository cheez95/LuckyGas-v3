"""Add dashboard performance indexes

Revision ID: add_dashboard_performance_indexes
Revises: 
Create Date: 2025-08-11 02:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_dashboard_performance_indexes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes to improve dashboard query performance."""
    
    # Orders table indexes
    op.create_index(
        'idx_orders_scheduled_date_status',
        'orders',
        ['scheduled_date', 'status'],
        postgresql_using='btree'
    )
    op.create_index(
        'idx_orders_customer_id',
        'orders',
        ['customer_id'],
        postgresql_using='btree'
    )
    op.create_index(
        'idx_orders_is_urgent',
        'orders',
        ['is_urgent'],
        postgresql_where=sa.text('is_urgent = true'),
        postgresql_using='btree'
    )
    op.create_index(
        'idx_orders_created_at',
        'orders',
        ['created_at'],
        postgresql_using='btree'
    )
    
    # Customers table indexes
    op.create_index(
        'idx_customers_is_active',
        'customers',
        ['is_active'],
        postgresql_where=sa.text('is_active = true'),
        postgresql_using='btree'
    )
    op.create_index(
        'idx_customers_area',
        'customers',
        ['area'],
        postgresql_using='btree'
    )
    
    # Routes table indexes
    op.create_index(
        'idx_routes_planned_date_status',
        'routes',
        ['planned_date', 'status'],
        postgresql_using='btree'
    )
    op.create_index(
        'idx_routes_driver_id',
        'routes',
        ['driver_id'],
        postgresql_using='btree'
    )
    
    # Delivery history table indexes
    op.create_index(
        'idx_delivery_history_delivered_at',
        'delivery_history',
        ['delivered_at'],
        postgresql_using='btree'
    )
    op.create_index(
        'idx_delivery_history_order_id',
        'delivery_history',
        ['order_id'],
        postgresql_using='btree'
    )
    op.create_index(
        'idx_delivery_history_status',
        'delivery_history',
        ['status'],
        postgresql_where=sa.text("status = 'delivered'"),
        postgresql_using='btree'
    )
    
    # Order items table indexes (for revenue calculation)
    op.create_index(
        'idx_order_items_order_id',
        'order_items',
        ['order_id'],
        postgresql_using='btree'
    )
    
    # Composite indexes for common join patterns
    op.create_index(
        'idx_orders_date_customer',
        'orders',
        ['scheduled_date', 'customer_id'],
        postgresql_using='btree'
    )
    
    # Partial index for today's data (frequently accessed)
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_orders_today 
        ON orders(scheduled_date, status) 
        WHERE scheduled_date >= CURRENT_DATE 
        AND scheduled_date < CURRENT_DATE + INTERVAL '1 day'
    """)
    
    # Partial index for active routes
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_routes_active 
        ON routes(planned_date, status) 
        WHERE status IN ('pending', 'in_progress')
    """)
    
    print("✅ Dashboard performance indexes created successfully")


def downgrade():
    """Remove dashboard performance indexes."""
    
    # Drop all indexes in reverse order
    op.drop_index('idx_routes_active', 'routes')
    op.drop_index('idx_orders_today', 'orders')
    op.drop_index('idx_orders_date_customer', 'orders')
    op.drop_index('idx_order_items_order_id', 'order_items')
    op.drop_index('idx_delivery_history_status', 'delivery_history')
    op.drop_index('idx_delivery_history_order_id', 'delivery_history')
    op.drop_index('idx_delivery_history_delivered_at', 'delivery_history')
    op.drop_index('idx_routes_driver_id', 'routes')
    op.drop_index('idx_routes_planned_date_status', 'routes')
    op.drop_index('idx_customers_area', 'customers')
    op.drop_index('idx_customers_is_active', 'customers')
    op.drop_index('idx_orders_created_at', 'orders')
    op.drop_index('idx_orders_is_urgent', 'orders')
    op.drop_index('idx_orders_customer_id', 'orders')
    op.drop_index('idx_orders_scheduled_date_status', 'orders')
    
    print("✅ Dashboard performance indexes removed")