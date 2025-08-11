"""Dashboard schemas for optimized API responses."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    """Main dashboard statistics."""
    
    today_orders: int = Field(0, description="Today's order count")
    today_revenue: float = Field(0.0, description="Today's revenue in TWD")
    active_customers: int = Field(0, description="Active customer count")
    drivers_on_route: int = Field(0, description="Drivers currently on route")
    recent_deliveries: int = Field(0, description="Recent delivery count")
    urgent_orders: int = Field(0, description="Urgent orders pending")
    completion_rate: float = Field(0.0, description="Overall completion rate percentage")
    
    class Config:
        orm_mode = True


class RouteProgress(BaseModel):
    """Route progress information."""
    
    id: int
    route_number: str
    status: str
    total_orders: int = 0
    completed_orders: int = 0
    driver_name: Optional[str] = None
    progress_percentage: float = Field(0.0, description="Progress percentage")
    
    class Config:
        orm_mode = True


class PredictionSummary(BaseModel):
    """AI prediction summary."""
    
    total: int = Field(0, description="Total predictions")
    urgent: int = Field(0, description="Urgent predictions")
    confidence: float = Field(0.0, description="Average confidence score")


class RealtimeActivity(BaseModel):
    """Real-time activity feed item."""
    
    id: str
    type: str = Field(..., description="Activity type: order, route, delivery, prediction")
    message: str
    timestamp: datetime
    status: str = Field(..., description="Status: info, success, warning")
    
    class Config:
        orm_mode = True


class DashboardSummary(BaseModel):
    """Complete dashboard summary response."""
    
    stats: DashboardStats
    routes: List[RouteProgress] = []
    predictions: Dict[str, Any] = Field(default_factory=dict)
    response_time_ms: int = Field(0, description="API response time in milliseconds")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "stats": {
                    "today_orders": 42,
                    "today_revenue": 25000.0,
                    "active_customers": 156,
                    "drivers_on_route": 3,
                    "recent_deliveries": 18,
                    "urgent_orders": 5,
                    "completion_rate": 75.5
                },
                "routes": [
                    {
                        "id": 1,
                        "route_number": "R001",
                        "status": "in_progress",
                        "total_orders": 10,
                        "completed_orders": 7,
                        "driver_name": "張三",
                        "progress_percentage": 70.0
                    }
                ],
                "predictions": {
                    "total": 25,
                    "urgent": 3,
                    "confidence": 0.85
                },
                "response_time_ms": 145
            }
        }