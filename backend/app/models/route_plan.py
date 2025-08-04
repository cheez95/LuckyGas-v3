"""
Route plan models for dispatch operations
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RouteStatus(str, enum.Enum):
    """Route plan status"""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StopStatus(str, enum.Enum):
    """Route stop status"""

    PENDING = "pending"
    ARRIVED = "arrived"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class RoutePlan(Base):
    """Route plan for a specific date and driver"""

    __tablename__ = "route_plans"

    id = Column(Integer, primary_key=True, index=True)
    route_date = Column(Date, nullable=False, index=True)
    route_number = Column(String(50), unique=True, nullable=False)

    # Driver assignment
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)

    # Route details
    status = Column(SQLEnum(RouteStatus), default=RouteStatus.PLANNED, nullable=False)
    total_stops = Column(Integer, default=0)
    completed_stops = Column(Integer, default=0)

    # Distance and time metrics
    total_distance_km = Column(Float, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    actual_duration_minutes = Column(Integer, nullable=True)

    # Timing
    planned_start_time = Column(DateTime, nullable=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)

    # Optimization details
    optimization_score = Column(Float, nullable=True)  # 0-100
    optimization_method = Column(String(50), nullable=True)  # google, manual, ai

    # Additional data
    route_data = Column(JSON, nullable=True)  # Polyline, bounds, etc.
    notes = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    driver = relationship(
        "User", foreign_keys=[driver_id], back_populates="assigned_routes"
    )
    stops = relationship(
        "RoutePlanStop", back_populates="route_plan", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_route_date_status", "route_date", "status"),
        Index("idx_driver_date", "driver_id", "route_date"),
    )

    def __repr__(self):
        return f"<RoutePlan {self.route_number} - {self.route_date}>"


class RoutePlanStop(Base):
    """Individual stop in a route plan"""

    __tablename__ = "route_plan_stops"
    __table_args__ = (
        UniqueConstraint(
            "route_plan_id", "stop_sequence", name="uq_route_plan_stop_sequence"
        ),
        Index("idx_plan_stop_status", "stop_status"),
        Index("idx_plan_order_route", "order_id", "route_plan_id"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    route_plan_id = Column(
        Integer, ForeignKey("route_plans.id"), nullable=False, index=True
    )
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)

    # Sequence and status
    stop_sequence = Column(Integer, nullable=False)  # Order of stops
    stop_status = Column(
        SQLEnum(StopStatus), default=StopStatus.PENDING, nullable=False
    )

    # Location details
    delivery_address = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Timing
    estimated_arrival = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    estimated_duration_minutes = Column(Integer, default=10)
    actual_duration_minutes = Column(Integer, nullable=True)

    # Delivery details
    delivered_qty_50kg = Column(Integer, default=0)
    delivered_qty_20kg = Column(Integer, default=0)
    delivered_qty_16kg = Column(Integer, default=0)
    delivered_qty_10kg = Column(Integer, default=0)
    delivered_qty_4kg = Column(Integer, default=0)

    # Completion details
    signature_image = Column(String(500), nullable=True)  # S3 URL
    photo_proof = Column(String(500), nullable=True)  # S3 URL
    stop_notes = Column(String(500), nullable=True)
    failure_reason = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    route_plan = relationship("RoutePlan", back_populates="stops")
    order = relationship("Order", backref="route_stops")

    # Additional constraints are defined below

    def __repr__(self):
        return f"<RoutePlanStop {self.route_plan_id}-{self.stop_sequence}>"


class DriverAssignment(Base):
    """Driver assignment history and scheduling"""

    __tablename__ = "driver_assignments"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    route_plan_id = Column(
        Integer, ForeignKey("route_plans.id"), nullable=False, index=True
    )

    # Assignment details
    assignment_date = Column(Date, nullable=False, index=True)
    assignment_type = Column(
        String(50), default="regular"
    )  # regular, emergency, substitute

    # Assignment metadata
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())

    # Confirmation
    is_confirmed = Column(Boolean, default=False)
    confirmed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(200), nullable=True)

    # Notes
    notes = Column(String(500), nullable=True)

    # Relationships
    driver = relationship("User", foreign_keys=[driver_id])
    route_plan = relationship("RoutePlan")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

    # Constraints
    __table_args__ = (
        UniqueConstraint("driver_id", "route_plan_id", name="uq_driver_route"),
        Index("idx_assignment_date", "assignment_date", "driver_id"),
    )

    def __repr__(self):
        return f"<DriverAssignment {self.driver_id}-{self.route_plan_id}>"
