from enum import Enum

from sqlalchemy import Boolean, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RouteStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    OPTIMIZED = "optimized"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    # Add simpler statuses for driver app
    PENDING = "pending"


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    route_number = Column(String(100), nullable=False, unique=True)
    name = Column(String(100))  # Alias for route_name
    route_name = Column(String(100))  # Keep for backward compatibility
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_date = Column(
        Date, nullable=False, index=True
    )  # Date only for driver queries
    route_date = Column(DateTime(timezone=True))  # Backward compatibility

    # Assignment
    driver_id = Column(
        Integer, ForeignKey("users.id")
    )  # Changed from drivers.id to users.id
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    # Route details
    area = Column(String(50))
    status = Column(SQLEnum(RouteStatus), default=RouteStatus.PENDING)  # Use enum
    total_stops = Column(Integer, default=0)
    completed_stops = Column(Integer, default=0)
    total_distance_km = Column(Float, default=0.0)
    estimated_duration_minutes = Column(Integer, default=0)
    polyline = Column(String(5000))  # For route visualization

    # Optimization
    is_optimized = Column(Boolean, default=False)
    optimization_score = Column(Float)  # 0.0 to 1.0
    optimization_timestamp = Column(DateTime(timezone=True))

    # Tracking
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    actual_duration_minutes = Column(Integer)

    # Active flag
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    stops = relationship(
        "RouteStop", back_populates="route", order_by="RouteStop.stop_sequence"
    )
    driver = relationship("User", backref="routes")


class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    # Sequence
    stop_sequence = Column(Integer, nullable=False)  # 1, 2, 3...

    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500), nullable=False)

    # Timing
    estimated_arrival = Column(DateTime(timezone=True))
    estimated_duration_minutes = Column(Integer, default=15)
    service_duration_minutes = Column(Integer, default=10)  # Time spent at stop
    actual_arrival = Column(DateTime(timezone=True))
    actual_departure = Column(DateTime(timezone=True))

    # Distance
    distance_from_previous_km = Column(Float, default=0.0)

    # Status
    is_completed = Column(Boolean, default=False)
    notes = Column(String(500))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    route = relationship("Route", back_populates="stops")
