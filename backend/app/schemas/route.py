from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.route import RouteStatus
from typing import Optional


class RouteStopBase(BaseModel):
    order_id: int
    stop_sequence: int
    latitude: float
    longitude: float
    address: str
    estimated_arrival: Optional[datetime] = None
    estimated_duration_minutes: int = 15


class RouteStopCreate(RouteStopBase):
    pass


class RouteStopUpdate(BaseModel):
    stop_sequence: Optional[int] = None
    estimated_arrival: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = None
    actual_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    is_completed: Optional[bool] = None
    notes: Optional[str] = None


class RouteStop(RouteStopBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    route_id: int
    distance_from_previous_km: float
    is_completed: bool
    actual_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class RouteBase(BaseModel):
    route_name: str
    route_date: datetime
    driver_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    area: Optional[str] = None


class RouteCreate(RouteBase):
    stops: Optional[List[RouteStopCreate]] = []


class RouteUpdate(BaseModel):
    route_name: Optional[str] = None
    route_date: Optional[datetime] = None
    driver_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    area: Optional[str] = None
    status: Optional[RouteStatus] = None


class Route(RouteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: RouteStatus
    total_stops: int
    total_distance_km: float
    estimated_duration_minutes: int

    is_optimized: bool
    optimization_score: Optional[float] = None
    optimization_timestamp: Optional[datetime] = None

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actual_duration_minutes: Optional[int] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    stops: List[RouteStop] = []


class RouteWithDetails(Route):
    """Route with additional details like driver and vehicle info"""

    driver_name: Optional[str] = None
    vehicle_plate: Optional[str] = None
    total_orders: int = 0
    completed_orders: int = 0
    total_cylinders: int = 0


class RouteOptimizationRequest(BaseModel):
    route_id: int
    use_time_windows: bool = True
    minimize_distance: bool = True
    balance_workload: bool = False


class RouteOptimizationResponse(BaseModel):
    route_id: int
    original_distance_km: float
    optimized_distance_km: float
    distance_saved_km: float
    distance_saved_percent: float
    original_duration_minutes: int
    optimized_duration_minutes: int
    time_saved_minutes: int
    optimization_score: float
    optimized_stops: List[RouteStop]


class AdjustmentRequest(BaseModel):
    """Request for route adjustment."""

    route_id: int
    order_id: int
    trigger: str = "manual"  # manual, emergency, delay, cancellation
    reason: Optional[str] = None


class AdjustmentResult(BaseModel):
    """Result of route adjustment."""

    success: bool
    route_id: int
    adjustment_type: str
    impact_minutes: int
    affected_stops: int
    message: str
    new_route: Optional["Route"] = None


# Alias for backward compatibility
RouteResponse = Route
RouteStopResponse = RouteStop
