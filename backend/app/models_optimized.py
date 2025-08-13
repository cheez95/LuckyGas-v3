"""
Optimized models for Lucky Gas - High Data, Low Concurrency Pattern
Designed for: 1,267 customers, 350,000+ deliveries, 15 concurrent users
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, 
    ForeignKey, Text, Enum, Index, Date, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# ============================================================================
# ENUMERATIONS
# ============================================================================

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    MANAGER = "manager"
    OFFICE_STAFF = "office_staff"
    DRIVER = "driver"
    CUSTOMER = "customer"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CustomerType(str, enum.Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    RESTAURANT = "restaurant"
    INDUSTRIAL = "industrial"
    OTHER = "other"


# ============================================================================
# CORE MODELS WITH OPTIMIZED INDEXES
# ============================================================================

class User(Base):
    """User model - Low volume, ~50 records"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)  # Index for filtering active users
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, index=True)  # Index for role-based queries
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        # Composite index for login queries
        Index('idx_user_username_active', 'username', 'is_active'),
    )


class Driver(Base):
    """Driver model - Low volume, ~20 records"""
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    vehicle_type = Column(String(50))
    license_plate = Column(String(20))
    max_daily_orders = Column(Integer, default=30)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        # Index for finding active drivers
        Index('idx_driver_active_code', 'is_active', 'code'),
    )


class Customer(Base):
    """Customer model - Medium volume, ~1,267 records"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(20), unique=True, index=True, nullable=False)  # Primary lookup
    invoice_title = Column(String(200))
    short_name = Column(String(100), nullable=False, index=True)  # For search
    address = Column(String(500), nullable=False)
    phone = Column(String(20))
    
    # Cylinder inventory
    cylinders_50kg = Column(Integer, default=0)
    cylinders_20kg = Column(Integer, default=0)
    cylinders_16kg = Column(Integer, default=0)
    cylinders_10kg = Column(Integer, default=0)
    
    # Location and type
    area = Column(String(50), index=True)  # Index for area-based queries
    customer_type = Column(Enum(CustomerType), default=CustomerType.RESIDENTIAL, index=True)
    
    # Subscription and status
    is_subscription = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Delivery preferences
    delivery_time_slot = Column(Integer)  # 0=全天, 1=早, 2=午, 3=晚
    preferred_delivery_day = Column(Integer)  # Day of week
    
    # Credit management
    credit_limit = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        # Composite indexes for common queries
        Index('idx_customer_area_active', 'area', 'is_active'),
        Index('idx_customer_type_active', 'customer_type', 'is_active'),
        Index('idx_customer_subscription', 'is_subscription', 'is_active'),
    )


class Order(Base):
    """Order model - High volume, growing daily"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Order details
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    order_date = Column(Date, index=True, nullable=False)  # Use Date instead of DateTime for better indexing
    delivery_date = Column(Date, index=True)
    
    # Cylinder quantities
    qty_50kg = Column(Integer, default=0)
    qty_20kg = Column(Integer, default=0)
    qty_16kg = Column(Integer, default=0)
    qty_10kg = Column(Integer, default=0)
    
    # Pricing
    total_amount = Column(Float, default=0.0)
    
    # Assignment
    driver_id = Column(Integer, ForeignKey("drivers.id"), index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), index=True)
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        # Critical indexes for order queries
        Index('idx_order_customer_date', 'customer_id', 'order_date'),  # Customer history
        Index('idx_order_date_status', 'order_date', 'status'),  # Daily operations
        Index('idx_order_delivery_date_status', 'delivery_date', 'status'),  # Delivery planning
        Index('idx_order_driver_date', 'driver_id', 'delivery_date'),  # Driver assignments
    )


class Route(Base):
    """Route model - Medium volume, ~100 per day"""
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String(50), unique=True, index=True, nullable=False)
    route_date = Column(Date, nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), index=True)
    
    # Route info
    total_stops = Column(Integer, default=0)
    completed_stops = Column(Integer, default=0)
    total_distance = Column(Float, default=0.0)
    
    # Optimization
    optimized_sequence = Column(Text)  # JSON array of stop order
    estimated_duration = Column(Integer)  # Minutes
    
    # Status
    is_optimized = Column(Boolean, default=False, index=True)
    is_completed = Column(Boolean, default=False, index=True)
    
    # Timestamps
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        # Indexes for route queries
        Index('idx_route_date', 'route_date'),  # Daily routes
        Index('idx_route_driver_date', 'driver_id', 'route_date'),  # Driver schedule
        Index('idx_route_date_completed', 'route_date', 'is_completed'),  # Completion tracking
        UniqueConstraint('driver_id', 'route_date', name='uq_driver_route_date'),  # One route per driver per day
    )


class Delivery(Base):
    """Active delivery model - Keep 6 months of data here"""
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)  # Denormalized for performance
    route_id = Column(Integer, ForeignKey("routes.id"), index=True)
    
    # Delivery info
    delivery_date = Column(Date, nullable=False, index=True)  # Use Date for better indexing
    delivered_at = Column(DateTime(timezone=True))
    
    # Proof of delivery
    signature = Column(Text)
    photo_url = Column(String(500))
    
    # Actual delivered quantities
    delivered_50kg = Column(Integer, default=0)
    delivered_20kg = Column(Integer, default=0)
    delivered_16kg = Column(Integer, default=0)
    delivered_10kg = Column(Integer, default=0)
    
    # Payment
    amount_collected = Column(Float, default=0.0)
    payment_method = Column(String(50))  # cash, transfer, credit
    
    # Status and notes
    is_successful = Column(Boolean, default=True, index=True)
    failure_reason = Column(Text)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # Critical indexes for delivery queries
        Index('idx_delivery_customer_date', 'customer_id', 'delivery_date'),  # Customer history - MOST IMPORTANT
        Index('idx_delivery_date', 'delivery_date'),  # Daily deliveries
        Index('idx_delivery_route', 'route_id'),  # Route deliveries
        Index('idx_delivery_date_success', 'delivery_date', 'is_successful'),  # Success tracking
    )


class DeliveryHistory(Base):
    """Historical delivery model - Data older than 6 months"""
    __tablename__ = "delivery_history"

    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, index=True)  # Original delivery ID
    order_id = Column(Integer, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    route_id = Column(Integer)
    
    # Delivery info (same as Delivery model)
    delivery_date = Column(Date, nullable=False, index=True)
    delivered_at = Column(DateTime(timezone=True))
    
    # Quantities
    delivered_50kg = Column(Integer, default=0)
    delivered_20kg = Column(Integer, default=0)
    delivered_16kg = Column(Integer, default=0)
    delivered_10kg = Column(Integer, default=0)
    
    # Payment
    amount_collected = Column(Float, default=0.0)
    payment_method = Column(String(50))
    
    # Status
    is_successful = Column(Boolean, default=True)
    failure_reason = Column(Text)
    notes = Column(Text)
    
    # Archive info
    archived_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # Minimal indexes for historical queries
        Index('idx_history_customer_date', 'customer_id', 'delivery_date'),  # Historical analysis
        Index('idx_history_date', 'delivery_date'),  # Date range queries
        Index('idx_history_original', 'original_id'),  # Lookup by original ID
    )


class OrderTemplate(Base):
    """Template for recurring orders - Low volume"""
    __tablename__ = "order_templates"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Template details
    template_name = Column(String(100))
    
    # Default quantities
    default_50kg = Column(Integer, default=0)
    default_20kg = Column(Integer, default=0)
    default_16kg = Column(Integer, default=0)
    default_10kg = Column(Integer, default=0)
    
    # Recurrence
    frequency_days = Column(Integer, default=30)
    next_order_date = Column(Date, index=True)  # Index for finding due templates
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    last_used = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        # Index for finding active templates due for ordering
        Index('idx_template_next_date', 'next_order_date', 'is_active'),
        Index('idx_template_customer_active', 'customer_id', 'is_active'),
    )


# ============================================================================
# MATERIALIZED VIEWS (Create these in PostgreSQL for reports)
# ============================================================================

"""
-- Daily delivery summary (refresh nightly)
CREATE MATERIALIZED VIEW daily_delivery_summary AS
SELECT 
    delivery_date,
    COUNT(*) as total_deliveries,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(DISTINCT route_id) as total_routes,
    SUM(CASE WHEN is_successful THEN 1 ELSE 0 END) as successful_deliveries,
    SUM(amount_collected) as total_collected,
    SUM(delivered_50kg) as total_50kg,
    SUM(delivered_20kg) as total_20kg
FROM deliveries
GROUP BY delivery_date
ORDER BY delivery_date DESC;

CREATE INDEX idx_daily_summary_date ON daily_delivery_summary(delivery_date);

-- Customer monthly summary (refresh weekly)
CREATE MATERIALIZED VIEW customer_monthly_summary AS
SELECT 
    customer_id,
    DATE_TRUNC('month', delivery_date) as month,
    COUNT(*) as delivery_count,
    SUM(amount_collected) as total_amount,
    AVG(delivered_50kg + delivered_20kg + delivered_16kg + delivered_10kg) as avg_cylinders
FROM deliveries
GROUP BY customer_id, DATE_TRUNC('month', delivery_date);

CREATE INDEX idx_customer_summary ON customer_monthly_summary(customer_id, month);
"""


# ============================================================================
# HELPER FUNCTIONS FOR DATA MANAGEMENT
# ============================================================================

async def archive_old_deliveries(db_session, months_to_keep=6):
    """Archive deliveries older than specified months to history table"""
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now().date() - timedelta(days=months_to_keep * 30)
    
    # Find deliveries to archive
    old_deliveries = db_session.query(Delivery).filter(
        Delivery.delivery_date < cutoff_date
    ).all()
    
    archived_count = 0
    for delivery in old_deliveries:
        # Create history record
        history = DeliveryHistory(
            original_id=delivery.id,
            order_id=delivery.order_id,
            customer_id=delivery.customer_id,
            route_id=delivery.route_id,
            delivery_date=delivery.delivery_date,
            delivered_at=delivery.delivered_at,
            delivered_50kg=delivery.delivered_50kg,
            delivered_20kg=delivery.delivered_20kg,
            delivered_16kg=delivery.delivered_16kg,
            delivered_10kg=delivery.delivered_10kg,
            amount_collected=delivery.amount_collected,
            payment_method=delivery.payment_method,
            is_successful=delivery.is_successful,
            failure_reason=delivery.failure_reason,
            notes=delivery.notes
        )
        db_session.add(history)
        db_session.delete(delivery)
        archived_count += 1
        
        # Commit in batches
        if archived_count % 1000 == 0:
            db_session.commit()
    
    db_session.commit()
    return archived_count


def get_customer_delivery_history(db_session, customer_id, limit=100):
    """Get customer delivery history from both active and archived tables"""
    from sqlalchemy import union_all
    
    # Query active deliveries
    active_query = db_session.query(
        Delivery.id,
        Delivery.delivery_date,
        Delivery.delivered_50kg,
        Delivery.delivered_20kg,
        Delivery.amount_collected,
        Delivery.is_successful
    ).filter(
        Delivery.customer_id == customer_id
    )
    
    # Query historical deliveries
    history_query = db_session.query(
        DeliveryHistory.original_id.label('id'),
        DeliveryHistory.delivery_date,
        DeliveryHistory.delivered_50kg,
        DeliveryHistory.delivered_20kg,
        DeliveryHistory.amount_collected,
        DeliveryHistory.is_successful
    ).filter(
        DeliveryHistory.customer_id == customer_id
    )
    
    # Combine and order
    combined = union_all(active_query, history_query).alias()
    result = db_session.query(combined).order_by(
        combined.c.delivery_date.desc()
    ).limit(limit).all()
    
    return result