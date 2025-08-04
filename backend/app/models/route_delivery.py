"""
Route delivery model - links routes to deliveries/orders
"""

from enum import Enum

from sqlalchemy import Boolean, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    ARRIVED = "arrived"
    DELIVERED = "delivered"
    FAILED = "failed"


class RouteDelivery(Base):
    """Link between routes and orders/deliveries"""

    __tablename__ = "route_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    # Sequence and status
    sequence = Column(Integer, nullable=False)  # Order in the route
    status = Column(
        SQLEnum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False
    )

    # Location (for actual delivery location)
    latitude = Column(Float)
    longitude = Column(Float)
    actual_address = Column(String(500))

    # Timing
    estimated_arrival = Column(DateTime(timezone=True))
    arrived_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))

    # Proof of delivery
    recipient_name = Column(String(100))
    signature_path = Column(String(500))  # Path to signature image
    photo_path = Column(String(500))  # Path to delivery photo

    # Notes and issues
    notes = Column(Text)
    issue_type = Column(String(50))  # absent, rejected, wrong_address, etc.

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    route = relationship("Route", backref="deliveries")
    order = relationship("Order", backref="route_delivery")


class DeliveryStatusHistory(Base):
    """Track all status changes for deliveries"""

    __tablename__ = "delivery_status_history"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("route_deliveries.id"), nullable=False)

    # Status change
    status = Column(SQLEnum(DeliveryStatus), nullable=False)
    notes = Column(Text)

    # Who made the change
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    delivery = relationship("RouteDelivery", backref="history")
    user = relationship("User")
