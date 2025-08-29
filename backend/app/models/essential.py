"""
Essential models for Lucky Gas - Only what's needed!
8 models instead of 44 - Simple, clean, maintainable
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Enum, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# ============================================================================
# ENUMERATIONS - Keep it simple!
# ============================================================================

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    MANAGER = "MANAGER"
    OFFICE_STAFF = "OFFICE_STAFF"
    DRIVER = "DRIVER"
    CUSTOMER = "CUSTOMER"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class DeliveryStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_ROUTE = "in_route"
    DELIVERED = "delivered"
    FAILED = "failed"


class CustomerType(str, enum.Enum):
    RESIDENTIAL = "residential"
    RESTAURANT = "restaurant"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"


class ProductType(str, enum.Enum):
    GAS_50KG = "gas_50kg"
    GAS_20KG = "gas_20kg"
    GAS_16KG = "gas_16kg"
    GAS_10KG = "gas_10kg"
    GAS_4KG = "gas_4kg"
    ACCESSORY = "accessory"


# ============================================================================
# MODELS - Simple and Direct!
# ============================================================================

class User(Base):
    """User model - for authentication and roles"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    driver = relationship("Driver", back_populates="user", uselist=False)


class Customer(Base):
    """Customer model - who we deliver to"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # Customer code
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50))
    email = Column(String(255))
    address = Column(Text, nullable=False)
    area = Column(String(100), index=True)  # Delivery area/zone
    
    # Business info
    customer_type = Column(Enum(CustomerType), default=CustomerType.RESIDENTIAL, index=True)
    pricing_tier = Column(String(50), default="standard")  # standard, premium, wholesale
    credit_limit = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    
    # Preferences
    preferred_delivery_time = Column(String(50))  # morning, afternoon, evening
    notes = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    
    # Indexes
    __table_args__ = (
        Index('idx_customer_type_active', 'customer_type', 'is_active'),
        Index('idx_customer_area', 'area'),
    )


class Product(Base):
    """Product model - what we sell"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    product_type = Column(Enum(ProductType), nullable=False, index=True)
    unit_price = Column(Float, nullable=False)
    
    # Stock info
    current_stock = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=10)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    """Order model - customer orders"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Order details
    order_date = Column(Date, nullable=False, index=True)
    delivery_date = Column(Date, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    
    # Financial
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    delivery = relationship("Delivery", back_populates="order", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_order_customer_date', 'customer_id', 'order_date'),
        Index('idx_order_status_date', 'status', 'order_date'),
        Index('idx_order_delivery_date', 'delivery_date'),
    )


class OrderItem(Base):
    """Order items - products in an order"""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class Driver(Base):
    """Driver model - who delivers"""
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    driver_code = Column(String(50), unique=True, index=True, nullable=False)
    license_number = Column(String(100), unique=True)
    phone = Column(String(50), nullable=False)
    
    # Capacity
    max_daily_deliveries = Column(Integer, default=30)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_available = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="driver")
    vehicles = relationship("Vehicle", back_populates="driver")
    deliveries = relationship("Delivery", back_populates="driver")


class Vehicle(Base):
    """Vehicle model - delivery vehicles"""
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), index=True)
    license_plate = Column(String(50), unique=True, index=True, nullable=False)
    vehicle_type = Column(String(50))  # truck, van, motorcycle
    capacity_kg = Column(Float)  # Max weight capacity
    
    # Maintenance
    last_maintenance = Column(Date)
    next_maintenance = Column(Date)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    driver = relationship("Driver", back_populates="vehicles")


class Delivery(Base):
    """Delivery model - actual deliveries"""
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), index=True)
    
    # Denormalized for performance (avoid joins for common queries)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Delivery details
    delivery_date = Column(Date, nullable=False, index=True)
    scheduled_time = Column(String(50))  # "09:00-12:00"
    actual_delivery_time = Column(DateTime)
    
    # Status
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.SCHEDULED, index=True)
    
    # Proof of delivery
    signature = Column(Text)
    signature_name = Column(String(255))
    photo_url = Column(String(500))
    
    # Notes
    delivery_notes = Column(Text)
    failure_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="delivery")
    driver = relationship("Driver", back_populates="deliveries")
    
    # Indexes - CRITICAL for your access patterns!
    __table_args__ = (
        Index('idx_delivery_customer_date', 'customer_id', 'delivery_date'),
        Index('idx_delivery_driver_date', 'driver_id', 'delivery_date'),
        Index('idx_delivery_status_date', 'status', 'delivery_date'),
    )