from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_async_session
from app.api.deps import get_current_user
from app.models.user import User
from app.models.delivery import DeliveryPrediction
from app.models.customer import Customer
from app.services.google_cloud.vertex_ai import demand_prediction_service
from app.schemas.prediction import (
    PredictionCreate,
    PredictionResponse,
    PredictionBatchResponse,
    PredictionMetrics,
    CustomerPrediction
)
from app.api.v1.websocket import notify_prediction_ready

router = APIRouter()


@router.post("/train", response_model=dict)
async def train_model(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Train or retrain the demand prediction model"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理員可以訓練模型"
        )
    
    result = await demand_prediction_service.train_demand_model()
    return result


@router.post("/batch", response_model=PredictionBatchResponse)
async def generate_batch_predictions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Generate batch predictions for all active customers"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="權限不足"
        )
    
    result = await demand_prediction_service.predict_demand_batch()
    
    # Send WebSocket notification
    await notify_prediction_ready(
        batch_id=result["batch_id"],
        summary=result["summary"]
    )
    
    return PredictionBatchResponse(**result)


@router.get("/customers/{customer_id}", response_model=CustomerPrediction)
async def get_customer_prediction(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get the latest prediction for a specific customer"""
    # Verify customer exists
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="客戶不存在"
        )
    
    prediction = await demand_prediction_service.get_customer_prediction(customer_id)
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="此客戶沒有預測資料"
        )
    
    return CustomerPrediction(**prediction)


@router.get("/", response_model=List[PredictionResponse])
async def list_predictions(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    confidence_threshold: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List predictions with optional filters"""
    query = select(DeliveryPrediction).order_by(desc(DeliveryPrediction.created_at))
    
    if customer_id:
        query = query.where(DeliveryPrediction.customer_id == customer_id)
    
    if start_date:
        query = query.where(DeliveryPrediction.predicted_date >= datetime.combine(start_date, datetime.min.time()))
    
    if end_date:
        query = query.where(DeliveryPrediction.predicted_date <= datetime.combine(end_date, datetime.max.time()))
    
    if confidence_threshold:
        query = query.where(DeliveryPrediction.confidence_score >= confidence_threshold)
    
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    predictions = result.scalars().all()
    
    return [
        PredictionResponse(
            id=p.id,
            customer_id=p.customer_id,
            predicted_date=p.predicted_date.date() if p.predicted_date else None,
            quantities={
                "50kg": p.predicted_quantity_50kg,
                "20kg": p.predicted_quantity_20kg,
                "16kg": p.predicted_quantity_16kg,
                "10kg": p.predicted_quantity_10kg,
                "4kg": p.predicted_quantity_4kg
            },
            confidence_score=p.confidence_score,
            model_version=p.model_version,
            is_converted_to_order=p.is_converted_to_order,
            created_at=p.created_at
        )
        for p in predictions
    ]


@router.get("/metrics", response_model=PredictionMetrics)
async def get_prediction_metrics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get prediction model performance metrics"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理員可以查看模型指標"
        )
    
    metrics = await demand_prediction_service.get_prediction_metrics()
    return PredictionMetrics(**metrics)


@router.post("/{prediction_id}/convert-to-order", response_model=dict)
async def convert_prediction_to_order(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Convert a prediction to an actual order"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="權限不足"
        )
    
    prediction = await session.get(DeliveryPrediction, prediction_id)
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="預測不存在"
        )
    
    if prediction.is_converted_to_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此預測已經轉換為訂單"
        )
    
    # TODO: Create order from prediction
    # This will be implemented when order creation is ready
    
    return {"message": "預測已轉換為訂單", "prediction_id": prediction_id}