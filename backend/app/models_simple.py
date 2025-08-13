"""
Simplified models for Lucky Gas local development.
Removes complex relationships and focuses on core functionality.
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, ForeignKey, Text, Enum
from sqlalchemy.sql import func

from app.core.database_simple import Base


# Enumerations
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


# Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    vehicle_type = Column(String(50))
    license_plate = Column(String(20))
    max_daily_orders = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(20), unique=True, index=True, nullable=False)
    invoice_title = Column(String(200))
    short_name = Column(String(100), nullable=False)
    address = Column(String(500), nullable=False)
    phone = Column(String(20))
    
    # Cylinder inventory (simplified)
    cylinders_50kg = Column(Integer, default=0)
    cylinders_20kg = Column(Integer, default=0)
    cylinders_16kg = Column(Integer, default=0)
    cylinders_10kg = Column(Integer, default=0)
    
    # Basic info
    area = Column(String(50))
    customer_type = Column(Enum(CustomerType), default=CustomerType.RESIDENTIAL)
    
    # Subscription and status
    is_subscription = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Order details
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    order_date = Column(DateTime(timezone=True), default=func.now())
    delivery_date = Column(DateTime(timezone=True))
    
    # Cylinder quantities
    qty_50kg = Column(Integer, default=0)
    qty_20kg = Column(Integer, default=0)
    qty_16kg = Column(Integer, default=0)
    qty_10kg = Column(Integer, default=0)
    
    # Pricing
    total_amount = Column(Float, default=0.0)
    
    # Assignment
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    route_id = Column(Integer, ForeignKey("routes.id"))
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    route_code = Column(String(50), unique=True, index=True, nullable=False)
    route_date = Column(DateTime(timezone=True), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    
    # Route info
    total_stops = Column(Integer, default=0)
    completed_stops = Column(Integer, default=0)
    total_distance = Column(Float, default=0.0)
    
    # Status
    is_optimized = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)
    
    # Timestamps
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id"))
    
    # Delivery info
    delivered_at = Column(DateTime(timezone=True))
    signature = Column(Text)
    photo_url = Column(String(500))
    
    # Actual delivered quantities
    delivered_50kg = Column(Integer, default=0)
    delivered_20kg = Column(Integer, default=0)
    delivered_16kg = Column(Integer, default=0)
    delivered_10kg = Column(Integer, default=0)
    
    # Status and notes
    is_successful = Column(Boolean, default=True)
    failure_reason = Column(Text)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OrderTemplate(Base):
    """Template for recurring orders"""
    __tablename__ = "order_templates"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Template details
    template_name = Column(String(100))
    
    # Default quantities
    default_50kg = Column(Integer, default=0)
    default_20kg = Column(Integer, default=0)
    default_16kg = Column(Integer, default=0)
    default_10kg = Column(Integer, default=0)
    
    # Recurrence
    frequency_days = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    last_used = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Notification(Base):
    """Simple notification system"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Notification details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50))  # info, warning, error, success
    
    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FeatureFlag(Base):
    """Feature flag for controlling functionality"""
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text)
    is_enabled = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())