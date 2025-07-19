from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from app.core.database import Base


class RouteStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    OPTIMIZED = "optimized"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Route(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, index=True)
    route_name = Column(String(100), nullable=False)
    route_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Assignment
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    
    # Route details
    area = Column(String(50))
    status = Column(SQLEnum(RouteStatus), default=RouteStatus.DRAFT)
    total_stops = Column(Integer, default=0)
    total_distance_km = Column(Float, default=0.0)
    estimated_duration_minutes = Column(Integer, default=0)
    
    # Optimization
    is_optimized = Column(Boolean, default=False)
    optimization_score = Column(Float)  # 0.0 to 1.0
    optimization_timestamp = Column(DateTime(timezone=True))
    
    # Tracking
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    actual_duration_minutes = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    stops = relationship("RouteStop", back_populates="route", order_by="RouteStop.stop_sequence")


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