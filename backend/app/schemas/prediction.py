from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PredictionType(str, Enum):
    demand = "demand"
    churn = "churn"
    route = "route"


class DemandPredictionRequest(BaseModel):
    prediction_date: datetime = Field(
        default_factory=lambda: datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ),
        description="Date for prediction",
    )
    customer_ids: Optional[List[str]] = Field(
        None, description="Specific customer IDs to predict"
    )
    confidence_threshold: Optional[float] = Field(
        0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )


class DemandPredictionResponse(BaseModel):
    customer_id: str
    customer_name: str
    predicted_demand: float = Field(..., description="Predicted demand quantity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    prediction_date: str
    recommended_action: Optional[str] = None


class ChurnPredictionResponse(BaseModel):
    customer_id: str
    churn_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: str = Field(..., description="high, medium, low")
    recommended_action: str
    days_since_last_order: Optional[int] = None
    avg_order_frequency: Optional[float] = None


class BatchPredictionRequest(BaseModel):
    model_type: PredictionType
    input_gcs_path: str = Field(..., description="GCS path to input data")
    output_gcs_path: str = Field(..., description="GCS path for output")
    parameters: Optional[Dict[str, Any]] = None


class BatchPredictionResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    input_path: str
    output_path: str
    estimated_completion: Optional[datetime] = None


class PredictionMetrics(BaseModel):
    demand_accuracy: float = Field(..., ge=0.0, le=1.0)
    churn_accuracy: float = Field(..., ge=0.0, le=1.0)
    route_optimization_score: float = Field(..., ge=0.0, le=1.0)
    total_predictions: int
    successful_predictions: int
    period_start: datetime
    period_end: datetime
    model_version: str
    last_training_date: datetime


class RouteOptimizationRequest(BaseModel):
    date: datetime = Field(default_factory=lambda: datetime.now())
    driver_ids: Optional[List[str]] = None
    order_ids: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "max_distance_per_route": 100,
            "max_stops_per_route": 20,
            "time_window_start": "08:00",
            "time_window_end": "18:00",
        }
    )


class RouteStop(BaseModel):
    sequence: int
    order_id: str
    customer_name: str
    address: str
    arrival_time: Optional[str] = None
    service_time: Optional[int] = Field(10, description="Service time in minutes")
    distance_from_prev: Optional[float] = Field(
        None, description="Distance from previous stop in km"
    )


class OptimizedRoute(BaseModel):
    route_id: str
    driver_id: str
    driver_name: str
    vehicle_number: Optional[str] = None
    stops: List[RouteStop]
    total_distance: float = Field(..., description="Total distance in km")
    total_time: int = Field(..., description="Total time in minutes")
    optimization_score: float = Field(..., ge=0.0, le=100.0)


class RouteOptimizationResponse(BaseModel):
    success: bool
    routes: List[OptimizedRoute]
    unassigned_orders: List[str]
    metrics: Dict[str, Any]
    optimization_score: float = Field(..., ge=0.0, le=100.0)
