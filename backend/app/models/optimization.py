"""Optimization data models for route optimization system."""

from datetime import datetime, time
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
)

from app.core.database import Base


class OptimizationConstraints(BaseModel):
    """Constraints for route optimization."""

    model_config = ConfigDict(from_attributes=True)

    max_route_duration_hours: float = Field(
        default=8.0, description="Maximum hours per route"
    )
    driver_shift_start: time = Field(
        default=time(9, 0), description="Driver shift start time"
    )
    driver_shift_end: time = Field(
        default=time(18, 0), description="Driver shift end time"
    )
    lunch_break_start: Optional[time] = Field(
        default=time(12, 0), description="Lunch break start"
    )
    lunch_break_duration_minutes: int = Field(
        default=60, description="Lunch break duration"
    )
    vehicle_capacity: Dict[str, int] = Field(
        default={"16kg": 20, "20kg": 16, "50kg": 8}, description="Max cylinders by type"
    )
    service_time_minutes: Dict[str, int] = Field(
        default={"residential": 5, "commercial": 10},
        description="Service time by customer type",
    )
    taiwan_peak_hours: List[Dict[str, time]] = Field(
        default=[
            {"start": time(7, 0), "end": time(9, 0)},
            {"start": time(17, 0), "end": time(19, 0)},
        ],
        description="Taiwan peak traffic hours",
    )
    max_stops_per_route: int = Field(default=30, description="Maximum stops per route")
    fuel_cost_per_km: float = Field(default=3.5, description="Fuel cost in TWD per km")
    time_cost_per_hour: float = Field(
        default=300.0, description="Labor cost in TWD per hour"
    )


class OptimizationRequest(BaseModel):
    """Request model for route optimization."""

    model_config = ConfigDict(from_attributes=True)

    date: datetime = Field(description="Date for route optimization")
    order_ids: List[int] = Field(description="List of order IDs to optimize")
    vehicle_ids: List[int] = Field(description="Available vehicle IDs")
    constraints: Optional[OptimizationConstraints] = Field(
        default_factory=OptimizationConstraints
    )
    optimization_mode: str = Field(default="balanced", pattern="^(time|fuel|balanced)$")
    allow_split_orders: bool = Field(
        default=False, description="Allow splitting large orders"
    )
    respect_time_windows: bool = Field(
        default=True, description="Enforce customer time windows"
    )
    cluster_radius_km: float = Field(
        default=5.0, description="Clustering radius in kilometers"
    )


class OptimizedStop(BaseModel):
    """Optimized stop in a route."""

    model_config = ConfigDict(from_attributes=True)

    order_id: int
    sequence: int
    arrival_time: datetime
    departure_time: datetime
    distance_from_previous_km: float
    travel_time_minutes: float
    service_time_minutes: int
    customer_id: int
    location: Dict[str, float] = Field(description="{'lat': float, 'lng': float}")
    delivery_notes: Optional[str] = None


class OptimizedRoute(BaseModel):
    """Optimized route result."""

    model_config = ConfigDict(from_attributes=True)

    route_id: Optional[int] = None
    vehicle_id: int
    driver_id: int
    date: datetime
    stops: List[OptimizedStop]
    total_distance_km: float
    total_duration_minutes: float
    total_fuel_cost: float
    total_time_cost: float
    total_cost: float
    start_location: Dict[str, float]
    end_location: Dict[str, float]
    capacity_utilization: Dict[str, int] = Field(
        description="Cylinders by type in route"
    )
    efficiency_score: float = Field(description="Route efficiency score 0 - 100")


class OptimizationResponse(BaseModel):
    """Response model for route optimization."""

    model_config = ConfigDict(from_attributes=True)

    optimization_id: str = Field(description="Unique optimization run ID")
    status: str = Field(pattern="^(success|partial|failed)$")
    routes: List[OptimizedRoute]
    unassigned_orders: List[int] = Field(default_factory=list)
    total_routes: int
    total_distance_km: float
    total_duration_hours: float
    total_cost: float
    savings_percentage: float = Field(description="Estimated savings vs unoptimized")
    optimization_time_ms: int
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OptimizationHistory(Base):
    """Store optimization run history for analysis."""

    __tablename__ = "optimization_history"

    id = Column(Integer, primary_key=True, index=True)
    optimization_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    request_data = Column(JSON)
    response_data = Column(JSON)
    optimization_mode = Column(String)
    total_orders = Column(Integer)
    total_routes = Column(Integer)
    total_distance_km = Column(Float)
    total_cost = Column(Float)
    savings_percentage = Column(Float)
    optimization_time_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(String, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "optimization_id": self.optimization_id,
            "created_at": self.created_at.isoformat(),
            "optimization_mode": self.optimization_mode,
            "total_orders": self.total_orders,
            "total_routes": self.total_routes,
            "total_distance_km": self.total_distance_km,
            "total_cost": self.total_cost,
            "savings_percentage": self.savings_percentage,
            "optimization_time_ms": self.optimization_time_ms,
            "success": self.success,
            "error_message": self.error_message,
        }


class ClusterInfo(BaseModel):
    """Information about geographic clusters."""

    model_config = ConfigDict(from_attributes=True)

    cluster_id: int
    center_lat: float
    center_lng: float
    order_ids: List[int]
    total_demand: Dict[str, int] = Field(description="Total cylinders by type")
    radius_km: float
    density_score: float = Field(description="Orders per square km")
