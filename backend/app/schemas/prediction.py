from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Dict, List, Optional, Any


class PredictionBase(BaseModel):
    customer_id: int
    predicted_date: date
    quantities: Dict[str, int]
    confidence_score: float = Field(ge=0.0, le=1.0)


class PredictionCreate(PredictionBase):
    pass


class PredictionResponse(PredictionBase):
    id: int
    model_version: Optional[str]
    is_converted_to_order: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class CustomerPrediction(BaseModel):
    customer_id: int
    predicted_date: str
    quantities: Dict[str, int]
    confidence_score: float
    model_version: Optional[str]
    created_at: str


class PredictionBatchResponse(BaseModel):
    batch_id: str
    predictions_count: int
    model_version: str
    execution_time_seconds: float
    timestamp: str
    summary: Dict[str, Any]


class PredictionMetrics(BaseModel):
    model_id: str
    accuracy_metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    last_training_date: str
    predictions_generated_today: int
    model_status: str


class PredictionTrainingResponse(BaseModel):
    model_id: str
    model_name: str
    status: str
    accuracy: float
    created_at: str
    training_hours: float
    features_used: List[str]