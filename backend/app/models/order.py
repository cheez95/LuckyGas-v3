from enum import Enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ASSIGNED = "assigned"
    IN_DELIVERY = "in_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    PARTIAL = "partial"
    REFUNDED = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # Order details
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    order_date = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_date = Column(DateTime(timezone=True))
    delivery_time_start = Column(String(5))  # "08:00"
    delivery_time_end = Column(String(5))  # "17:00"

    # Cylinder quantities
    qty_50kg = Column(Integer, default=0)
    qty_20kg = Column(Integer, default=0)
    qty_16kg = Column(Integer, default=0)
    qty_10kg = Column(Integer, default=0)
    qty_4kg = Column(Integer, default=0)

    # Pricing
    total_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, default=0.0)

    # Payment
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.UNPAID)
    payment_method = Column(String(50))
    invoice_number = Column(String(50))

    # Delivery info
    delivery_address = Column(String(500))
    delivery_notes = Column(String(500))
    is_urgent = Column(Boolean, default=False)

    # Assignment
    route_id = Column(Integer, ForeignKey("routes.id"))
    driver_id = Column(Integer, ForeignKey("users.id"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    delivered_at = Column(DateTime(timezone=True))

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    delivery = relationship("Delivery", back_populates="order", uselist=False)
    order_items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    invoice = relationship("Invoice", back_populates="order", uselist=False)
