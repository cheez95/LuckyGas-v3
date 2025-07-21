"""
Add performance indexes for optimized database queries
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def create_indexes():
    """Create performance-critical database indexes"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    indexes = [
        # Customer indexes
        "CREATE INDEX IF NOT EXISTS idx_customer_area ON customers(area);",
        "CREATE INDEX IF NOT EXISTS idx_customer_is_terminated ON customers(is_terminated);",
        "CREATE INDEX IF NOT EXISTS idx_customer_code ON customers(customer_code);",
        "CREATE INDEX IF NOT EXISTS idx_customer_short_name ON customers(short_name);",
        
        # Order indexes
        "CREATE INDEX IF NOT EXISTS idx_order_customer_id ON orders(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_order_status ON orders(status);",
        "CREATE INDEX IF NOT EXISTS idx_order_scheduled_date ON orders(scheduled_date);",
        "CREATE INDEX IF NOT EXISTS idx_order_is_urgent ON orders(is_urgent);",
        "CREATE INDEX IF NOT EXISTS idx_order_route_id ON orders(route_id);",
        "CREATE INDEX IF NOT EXISTS idx_order_driver_id ON orders(driver_id);",
        "CREATE INDEX IF NOT EXISTS idx_order_created_at ON orders(created_at);",
        
        # Composite indexes for common queries
        "CREATE INDEX IF NOT EXISTS idx_order_status_scheduled_date ON orders(status, scheduled_date);",
        "CREATE INDEX IF NOT EXISTS idx_order_customer_status ON orders(customer_id, status);",
        
        # Route indexes
        "CREATE INDEX IF NOT EXISTS idx_route_route_date ON delivery_routes(route_date);",
        "CREATE INDEX IF NOT EXISTS idx_route_driver_id ON delivery_routes(driver_id);",
        "CREATE INDEX IF NOT EXISTS idx_route_status ON delivery_routes(status);",
        "CREATE INDEX IF NOT EXISTS idx_route_area ON delivery_routes(area);",
        "CREATE INDEX IF NOT EXISTS idx_route_vehicle_id ON delivery_routes(vehicle_id);",
        
        # Composite indexes for route queries
        "CREATE INDEX IF NOT EXISTS idx_route_date_status ON delivery_routes(route_date, status);",
        "CREATE INDEX IF NOT EXISTS idx_route_driver_date ON delivery_routes(driver_id, route_date);",
        
        # Route stop indexes
        "CREATE INDEX IF NOT EXISTS idx_route_stop_route_id ON route_stops(route_id);",
        "CREATE INDEX IF NOT EXISTS idx_route_stop_order_id ON route_stops(order_id);",
        "CREATE INDEX IF NOT EXISTS idx_route_stop_sequence ON route_stops(route_id, stop_sequence);",
        "CREATE INDEX IF NOT EXISTS idx_route_stop_completed ON route_stops(is_completed);",
        
        # User indexes
        "CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);",
        "CREATE INDEX IF NOT EXISTS idx_user_role ON users(role);",
        "CREATE INDEX IF NOT EXISTS idx_user_is_active ON users(is_active);",
        
        # Vehicle indexes
        "CREATE INDEX IF NOT EXISTS idx_vehicle_is_active ON vehicles(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_vehicle_is_available ON vehicles(is_available);",
        "CREATE INDEX IF NOT EXISTS idx_vehicle_vehicle_type ON vehicles(vehicle_type);",
        
        # Gas product indexes
        "CREATE INDEX IF NOT EXISTS idx_gas_product_is_available ON gas_products(is_available);",
        "CREATE INDEX IF NOT EXISTS idx_gas_product_cylinder_type ON gas_products(cylinder_type);",
        
        # Customer inventory indexes
        "CREATE INDEX IF NOT EXISTS idx_customer_inventory_customer_id ON customer_inventories(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_customer_inventory_product_id ON customer_inventories(gas_product_id);",
        "CREATE INDEX IF NOT EXISTS idx_customer_inventory_is_active ON customer_inventories(is_active);",
        
        # Order item indexes
        "CREATE INDEX IF NOT EXISTS idx_order_item_order_id ON order_items(order_id);",
        "CREATE INDEX IF NOT EXISTS idx_order_item_product_id ON order_items(gas_product_id);",
        
        # Delivery history indexes
        "CREATE INDEX IF NOT EXISTS idx_delivery_history_order_id ON delivery_histories(order_id);",
        "CREATE INDEX IF NOT EXISTS idx_delivery_history_customer_id ON delivery_histories(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_delivery_history_driver_id ON delivery_histories(driver_id);",
        "CREATE INDEX IF NOT EXISTS idx_delivery_history_delivered_at ON delivery_histories(delivered_at);",
        
        # Prediction indexes
        "CREATE INDEX IF NOT EXISTS idx_prediction_customer_id ON demand_predictions(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_prediction_date ON demand_predictions(prediction_date);",
        "CREATE INDEX IF NOT EXISTS idx_prediction_type ON demand_predictions(prediction_type);",
        
        # Full-text search indexes for Traditional Chinese
        "CREATE INDEX IF NOT EXISTS idx_customer_search ON customers USING gin(to_tsvector('simple', short_name || ' ' || invoice_title || ' ' || address));",
        "CREATE INDEX IF NOT EXISTS idx_order_search ON orders USING gin(to_tsvector('simple', order_number || ' ' || delivery_address || ' ' || COALESCE(delivery_notes, '')));"
    ]
    
    with Session(engine) as session:
        for index_sql in indexes:
            try:
                session.execute(text(index_sql))
                logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                logger.warning(f"Failed to create index: {e}")
        
        session.commit()
        logger.info("All database indexes created successfully")


def drop_indexes():
    """Drop all custom indexes (for rollback)"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    index_names = [
        # Customer indexes
        "idx_customer_area",
        "idx_customer_is_terminated",
        "idx_customer_code",
        "idx_customer_short_name",
        
        # Order indexes
        "idx_order_customer_id",
        "idx_order_status",
        "idx_order_scheduled_date",
        "idx_order_is_urgent",
        "idx_order_route_id",
        "idx_order_driver_id",
        "idx_order_created_at",
        "idx_order_status_scheduled_date",
        "idx_order_customer_status",
        
        # Route indexes
        "idx_route_route_date",
        "idx_route_driver_id",
        "idx_route_status",
        "idx_route_area",
        "idx_route_vehicle_id",
        "idx_route_date_status",
        "idx_route_driver_date",
        
        # Route stop indexes
        "idx_route_stop_route_id",
        "idx_route_stop_order_id",
        "idx_route_stop_sequence",
        "idx_route_stop_completed",
        
        # Other indexes
        "idx_user_email",
        "idx_user_role",
        "idx_user_is_active",
        "idx_vehicle_is_active",
        "idx_vehicle_is_available",
        "idx_vehicle_vehicle_type",
        "idx_gas_product_is_available",
        "idx_gas_product_cylinder_type",
        "idx_customer_inventory_customer_id",
        "idx_customer_inventory_product_id",
        "idx_customer_inventory_is_active",
        "idx_order_item_order_id",
        "idx_order_item_product_id",
        "idx_delivery_history_order_id",
        "idx_delivery_history_customer_id",
        "idx_delivery_history_driver_id",
        "idx_delivery_history_delivered_at",
        "idx_prediction_customer_id",
        "idx_prediction_date",
        "idx_prediction_type",
        "idx_customer_search",
        "idx_order_search"
    ]
    
    with Session(engine) as session:
        for index_name in index_names:
            try:
                session.execute(text(f"DROP INDEX IF EXISTS {index_name};"))
                logger.info(f"Dropped index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to drop index {index_name}: {e}")
        
        session.commit()
        logger.info("All database indexes dropped successfully")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("Rolling back database indexes...")
        drop_indexes()
    else:
        print("Creating database indexes...")
        create_indexes()