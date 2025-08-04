"""
Google Routes API Configuration

This module contains configuration constants and parameters for the Google Routes API integration.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import time


class RoutesAPIConfig(BaseModel):
    """Configuration for Google Routes API"""

    # API Endpoints
    compute_routes_url: str = (
        "https://routes.googleapis.com/directions/v2:computeRoutes"
    )
    compute_matrix_url: str = (
        "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    )
    optimization_url_template: str = (
        "https://routes.googleapis.com/v1/projects/{project}/locations/{location}/routeOptimization:optimizeTours"
    )

    # Rate Limiting
    requests_per_second: int = Field(10, description="Maximum requests per second")
    requests_per_day: int = Field(25000, description="Maximum requests per day")

    # Retry Configuration
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    initial_retry_delay: float = Field(
        1.0, description="Initial retry delay in seconds"
    )
    backoff_multiplier: float = Field(2.0, description="Exponential backoff multiplier")
    max_retry_delay: float = Field(32.0, description="Maximum retry delay in seconds")

    # Request Configuration
    default_travel_mode: str = "DRIVE"
    default_routing_preference: str = "TRAFFIC_AWARE_OPTIMAL"
    default_language: str = "zh-TW"
    default_region: str = "TW"
    default_units: str = "METRIC"

    # Taiwan-specific Configuration
    avoid_tolls: bool = Field(False, description="Taiwan has limited toll roads")
    avoid_highways: bool = Field(
        False, description="Highways are often faster in Taiwan"
    )
    avoid_ferries: bool = Field(True, description="Avoid ferries for reliability")
    avoid_indoor: bool = Field(True, description="Avoid indoor navigation")

    # Optimization Parameters
    optimize_waypoint_order: bool = Field(True, description="Allow route optimization")
    compute_alternative_routes: bool = Field(
        False, description="Skip alternatives to save costs"
    )
    requested_reference_routes: List[str] = Field(
        default=["FUEL_EFFICIENT"], description="Reference routes for comparison"
    )
    extra_computations: List[str] = Field(
        default=["TOLLS", "FUEL_CONSUMPTION"], description="Additional data to compute"
    )

    # Field Masks (to reduce response size and costs)
    default_field_mask: str = Field(
        default="routes.duration,routes.distanceMeters,routes.polyline,routes.optimizedIntermediateWaypointIndex,routes.legs",
        description="Default fields to request",
    )
    matrix_field_mask: str = Field(
        default="originIndex,destinationIndex,distanceMeters,duration,status",
        description="Fields for distance matrix",
    )

    # Cost Management
    cost_per_request: float = Field(
        0.005, description="Estimated cost per API request in USD"
    )
    daily_budget_usd: float = Field(50.0, description="Daily budget limit in USD")
    monthly_budget_usd: float = Field(1000.0, description="Monthly budget limit in USD")

    # Cache Configuration
    cache_ttl_seconds: int = Field(3600, description="Cache time-to-live in seconds")
    max_cache_size_mb: int = Field(100, description="Maximum cache size in MB")

    # Business Hours (Taiwan time)
    business_start_time: time = Field(
        default=time(8, 0), description="Business start time"
    )
    business_end_time: time = Field(
        default=time(18, 0), description="Business end time"
    )

    # Vehicle Configuration
    default_vehicle_capacity: Dict[str, int] = Field(
        default={"50kg": 10, "20kg": 20, "16kg": 25, "10kg": 40, "4kg": 50},
        description="Default vehicle capacity by cylinder size",
    )

    # Service Time Configuration
    base_service_time_minutes: int = Field(5, description="Base time at each stop")
    time_per_cylinder_minutes: int = Field(
        2, description="Additional time per cylinder"
    )

    # Distance and Time Thresholds
    max_route_distance_km: float = Field(200.0, description="Maximum route distance")
    max_route_duration_hours: float = Field(8.0, description="Maximum route duration")
    max_stops_per_route: int = Field(50, description="Maximum stops per route")

    class Config:
        schema_extra = {
            "example": {
                "requests_per_second": 10,
                "max_retries": 3,
                "default_language": "zh-TW",
                "daily_budget_usd": 50.0,
            }
        }


class RouteOptimizationRequest(BaseModel):
    """Request model for route optimization"""

    depot: tuple[float, float] = Field(..., description="Depot coordinates (lat, lng)")
    stops: List[Dict] = Field(..., description="List of delivery stops")
    vehicle_capacity: Optional[Dict[str, int]] = Field(
        None, description="Vehicle capacity by product type"
    )
    time_windows: Optional[Dict] = Field(None, description="Time window constraints")
    departure_time: Optional[str] = Field(None, description="ISO 8601 departure time")
    traffic_model: str = Field("BEST_GUESS", description="Traffic prediction model")
    optimize_for: str = Field(
        "TIME", description="Optimization objective: TIME or DISTANCE"
    )


class RouteOptimizationResponse(BaseModel):
    """Response model for route optimization"""

    stops: List[Dict] = Field(..., description="Optimized list of stops")
    total_distance: int = Field(..., description="Total distance in meters")
    total_duration: str = Field(..., description="Total duration in seconds format")
    total_duration_minutes: int = Field(..., description="Total duration in minutes")
    polyline: str = Field(..., description="Encoded route polyline")
    warnings: List[str] = Field(default=[], description="Any warnings from the API")
    optimized: bool = Field(..., description="Whether route was optimized")
    optimization_savings: Optional[Dict] = Field(
        None, description="Savings from optimization"
    )
    fuel_consumption_liters: Optional[float] = Field(
        None, description="Estimated fuel consumption"
    )
    toll_info: Optional[Dict] = Field(None, description="Toll information if available")


# Default configuration instance
default_routes_config = RoutesAPIConfig()


# Error code mapping for better error handling
GOOGLE_API_ERROR_CODES = {
    400: "INVALID_REQUEST",
    401: "UNAUTHENTICATED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    429: "RESOURCE_EXHAUSTED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}


# Taiwan-specific constants
TAIWAN_REGIONS = {
    "台北市": {"lat": 25.0330, "lng": 121.5654},
    "新北市": {"lat": 25.0170, "lng": 121.4627},
    "桃園市": {"lat": 24.9936, "lng": 121.3010},
    "台中市": {"lat": 24.1477, "lng": 120.6736},
    "台南市": {"lat": 22.9998, "lng": 120.2268},
    "高雄市": {"lat": 22.6273, "lng": 120.3014},
}


# Traffic patterns for Taiwan (peak hours)
TAIWAN_TRAFFIC_PATTERNS = {
    "morning_peak": {"start": "07:00", "end": "09:00", "factor": 1.5},
    "lunch_time": {"start": "11:30", "end": "13:30", "factor": 1.2},
    "evening_peak": {"start": "17:00", "end": "19:30", "factor": 1.6},
    "night_time": {"start": "22:00", "end": "06:00", "factor": 0.8},
}
