from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, insert
from typing import List, Optional
from datetime import datetime, date
import logging

from app.core.database import get_async_session, async_session_maker
from app.api.deps import get_current_user
from app.models.user import User
from app.models.delivery import DeliveryPrediction
from app.models.customer import Customer
from app.models.prediction_batch import PredictionBatch
from app.core.google_cloud_config import get_gcp_config

logger = logging.getLogger(__name__)

# Import the appropriate service based on configuration
gcp_config = get_gcp_config()
if gcp_config.is_vertex_ai_configured():
    from app.services.google_cloud.vertex_ai_service import vertex_ai_service as demand_prediction_service
else:
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


async def process_batch_predictions(batch_id: int, user_id: int):
    """Background task for processing batch predictions"""
    async with async_session_maker() as session:
        try:
            # Update batch status to processing
            batch = await session.get(PredictionBatch, batch_id)
            batch.status = "processing"
            batch.started_at = datetime.utcnow()
            await session.commit()
            
            # Get all active customers
            result = await session.execute(
                select(Customer).where(Customer.is_terminated == False)
            )
            customers = result.scalars().all()
            batch.total_customers = len(customers)
            await session.commit()
            
            # Generate predictions
            predictions_data = []
            successful = 0
            failed = 0
            
            for customer in customers:
                try:
                    # Get prediction from service
                    prediction = await demand_prediction_service.predict_for_customer(
                        customer_id=customer.id,
                        customer_data={
                            "avg_daily_usage": customer.avg_daily_usage or 0.5,
                            "max_cycle_days": customer.max_cycle_days or 30,
                            "cylinders_50kg": customer.cylinders_50kg,
                            "cylinders_20kg": customer.cylinders_20kg,
                            "cylinders_16kg": customer.cylinders_16kg,
                            "cylinders_10kg": customer.cylinders_10kg,
                            "cylinders_4kg": customer.cylinders_4kg,
                        }
                    )
                    
                    if prediction:
                        predictions_data.append({
                            "customer_id": customer.id,
                            "predicted_date": prediction["predicted_date"],
                            "predicted_quantity_50kg": prediction.get("quantities", {}).get("50kg", 0),
                            "predicted_quantity_20kg": prediction.get("quantities", {}).get("20kg", 0),
                            "predicted_quantity_16kg": prediction.get("quantities", {}).get("16kg", 0),
                            "predicted_quantity_10kg": prediction.get("quantities", {}).get("10kg", 0),
                            "predicted_quantity_4kg": prediction.get("quantities", {}).get("4kg", 0),
                            "confidence_score": prediction.get("confidence_score", 0.8),
                            "model_version": "v1.0",
                            "batch_id": batch_id
                        })
                        successful += 1
                    
                except Exception as e:
                    logger.error(f"Failed to predict for customer {customer.id}: {e}")
                    failed += 1
                
                # Update progress
                batch.processed_customers = successful + failed
                if batch.processed_customers % 10 == 0:  # Update every 10 customers
                    await session.commit()
            
            # Bulk insert predictions
            if predictions_data:
                await session.execute(
                    insert(DeliveryPrediction).values(predictions_data)
                )
            
            # Update batch status
            batch.status = "completed"
            batch.completed_at = datetime.utcnow()
            batch.successful_predictions = successful
            batch.failed_predictions = failed
            await session.commit()
            
            # Send WebSocket notification
            await notify_prediction_ready(
                batch_id=batch_id,
                summary={
                    "total": batch.total_customers,
                    "successful": successful,
                    "failed": failed
                }
            )
            
            logger.info(f"Batch prediction {batch_id} completed: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"Batch prediction {batch_id} failed: {e}")
            # Update batch with error
            batch = await session.get(PredictionBatch, batch_id)
            batch.status = "failed"
            batch.error_message = str(e)
            batch.completed_at = datetime.utcnow()
            await session.commit()


@router.post("/batch", response_model=dict)
async def generate_batch_predictions(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Generate batch predictions for all active customers"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="權限不足"
        )
    
    # Create batch record
    batch = PredictionBatch(
        created_by=current_user.id,
        status="pending"
    )
    session.add(batch)
    await session.commit()
    await session.refresh(batch)
    
    # Add to background tasks
    background_tasks.add_task(
        process_batch_predictions,
        batch_id=batch.id,
        user_id=current_user.id
    )
    
    return {
        "batch_id": batch.id,
        "status": "processing",
        "message": "預測生成已開始，完成後將通知您"
    }


@router.get("/batch/{batch_id}", response_model=dict)
async def get_batch_status(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get the status of a prediction batch"""
    batch = await session.get(PredictionBatch, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="批次不存在"
        )
    
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "total_customers": batch.total_customers,
        "processed_customers": batch.processed_customers,
        "successful_predictions": batch.successful_predictions,
        "failed_predictions": batch.failed_predictions,
        "error_message": batch.error_message,
        "created_at": batch.created_at,
        "started_at": batch.started_at,
        "completed_at": batch.completed_at
    }


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