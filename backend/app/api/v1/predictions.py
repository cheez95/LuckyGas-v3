from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.prediction import (
    DemandPredictionRequest,
    DemandPredictionResponse,
    ChurnPredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionMetrics
)
from app.services.vertex_ai_service import vertex_ai_service
from app.core.decorators import rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/demand/daily", response_model=List[DemandPredictionResponse])
@rate_limit(requests_per_minute=10)
async def predict_daily_demand(
    request: DemandPredictionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Predict daily demand for customers.
    
    - **prediction_date**: Date for prediction (defaults to tomorrow)
    - **customer_ids**: Optional list of customer IDs (all if not specified)
    - **confidence_threshold**: Minimum confidence for predictions (0.0-1.0)
    """
    try:
        # Get customer data from database
        customer_data = []
        
        if request.customer_ids:
            # Get specific customers
            # TODO: Implement database query
            customer_data = [
                {
                    "id": f"CUST{i:04d}",
                    "name": f"Customer {i}",
                    "cylinder_type": "20kg",
                    "days_since_last_order": i * 2,
                    "avg_consumption": 20 + i % 10,
                }
                for i in range(1, len(request.customer_ids) + 1)
            ]
        else:
            # Get all active customers
            # TODO: Implement database query
            customer_data = [
                {
                    "id": f"CUST{i:04d}",
                    "name": f"Customer {i}",
                    "cylinder_type": "20kg",
                    "days_since_last_order": i % 30,
                    "avg_consumption": 20 + i % 10,
                }
                for i in range(1, 51)
            ]
        
        # Make predictions
        predictions = await vertex_ai_service.predict_daily_demand(
            customer_data,
            request.prediction_date
        )
        
        # Filter by confidence threshold
        if request.confidence_threshold:
            predictions = [
                p for p in predictions 
                if p["confidence"] >= request.confidence_threshold
            ]
        
        # Sort by predicted demand (highest first)
        predictions.sort(key=lambda x: x["predicted_demand"], reverse=True)
        
        return predictions
        
    except Exception as e:
        logger.error(f"Error predicting daily demand: {str(e)}")
        raise HTTPException(status_code=500, detail="預測需求時發生錯誤")

@router.get("/demand/weekly", response_model=Dict[str, List[DemandPredictionResponse]])
async def predict_weekly_demand(
    start_date: Optional[datetime] = Query(None, description="Start date for prediction"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Predict demand for the next 7 days.
    """
    try:
        if not start_date:
            start_date = datetime.now() + timedelta(days=1)
        
        # Get all active customers
        # TODO: Implement database query
        customer_data = [
            {
                "id": f"CUST{i:04d}",
                "name": f"Customer {i}",
                "cylinder_type": "20kg",
                "days_since_last_order": i % 30,
                "avg_consumption": 20 + i % 10,
            }
            for i in range(1, 101)
        ]
        
        weekly_predictions = {}
        
        for day in range(7):
            prediction_date = start_date + timedelta(days=day)
            date_str = prediction_date.strftime("%Y-%m-%d")
            
            predictions = await vertex_ai_service.predict_daily_demand(
                customer_data,
                prediction_date
            )
            
            # Keep top 20 predictions per day
            weekly_predictions[date_str] = predictions[:20]
        
        return weekly_predictions
        
    except Exception as e:
        logger.error(f"Error predicting weekly demand: {str(e)}")
        raise HTTPException(status_code=500, detail="預測每週需求時發生錯誤")

@router.post("/churn", response_model=List[ChurnPredictionResponse])
async def predict_customer_churn(
    customer_ids: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Predict customer churn probability.
    """
    try:
        # Get customer data
        if customer_ids:
            # Get specific customers
            # TODO: Implement database query
            customers = [
                {
                    "id": f"CUST{i:04d}",
                    "days_since_last_order": i * 10,
                    "total_orders": 100 - i * 2,
                    "avg_order_frequency": 30,
                    "customer_type": "residential",
                    "payment_delays": i % 5,
                    "complaints": i % 3,
                }
                for i in range(1, len(customer_ids) + 1)
            ]
        else:
            # Get all customers with potential churn
            # TODO: Implement database query
            customers = [
                {
                    "id": f"CUST{i:04d}",
                    "days_since_last_order": i * 5,
                    "total_orders": 100 - i,
                    "avg_order_frequency": 30,
                    "customer_type": "residential" if i % 2 else "commercial",
                    "payment_delays": i % 5,
                    "complaints": i % 3,
                }
                for i in range(1, 21)
            ]
        
        # Make predictions
        churn_predictions = []
        for customer in customers:
            prediction = await vertex_ai_service.predict_customer_churn(customer)
            churn_predictions.append(prediction)
        
        # Sort by churn probability (highest risk first)
        churn_predictions.sort(key=lambda x: x["churn_probability"], reverse=True)
        
        return churn_predictions
        
    except Exception as e:
        logger.error(f"Error predicting customer churn: {str(e)}")
        raise HTTPException(status_code=500, detail="預測客戶流失時發生錯誤")

@router.post("/batch", response_model=BatchPredictionResponse)
async def create_batch_prediction(
    request: BatchPredictionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a batch prediction job.
    """
    try:
        # Create batch prediction job
        job_id = await vertex_ai_service.batch_predict(
            input_uri=request.input_gcs_path,
            output_uri=request.output_gcs_path,
            model_endpoint=request.model_type,
            job_display_name=f"batch-prediction-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        
        return BatchPredictionResponse(
            job_id=job_id,
            status="running",
            created_at=datetime.now(),
            input_path=request.input_gcs_path,
            output_path=request.output_gcs_path
        )
        
    except Exception as e:
        logger.error(f"Error creating batch prediction: {str(e)}")
        raise HTTPException(status_code=500, detail="建立批次預測時發生錯誤")

@router.get("/metrics", response_model=PredictionMetrics)
async def get_prediction_metrics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get prediction accuracy metrics.
    """
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        # TODO: Implement actual metrics calculation from database
        # For now, return sample metrics
        
        return PredictionMetrics(
            demand_accuracy=0.85,
            churn_accuracy=0.78,
            route_optimization_score=0.82,
            total_predictions=1523,
            successful_predictions=1295,
            period_start=start_date,
            period_end=end_date,
            model_version="v1.0.0",
            last_training_date=datetime.now() - timedelta(days=7)
        )
        
    except Exception as e:
        logger.error(f"Error getting prediction metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取預測指標時發生錯誤")

@router.post("/train/demand-model")
@rate_limit(requests_per_minute=1)
async def train_demand_model(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger training of demand prediction model.
    Requires admin privileges.
    """
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="需要管理員權限")
    
    try:
        # Prepare training data
        training_data = await vertex_ai_service.prepare_historical_data_for_training()
        
        # Upload to GCS
        dataset_path = await vertex_ai_service.upload_training_data(
            training_data,
            f"demand-prediction-{datetime.now().strftime('%Y%m%d')}"
        )
        
        # Start training
        model_name = await vertex_ai_service.train_demand_prediction_model(
            dataset_path,
            display_name=f"lucky-gas-demand-{datetime.now().strftime('%Y%m%d')}"
        )
        
        return {
            "success": True,
            "model_name": model_name,
            "dataset_path": dataset_path,
            "training_started": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error training demand model: {str(e)}")
        raise HTTPException(status_code=500, detail="訓練模型時發生錯誤")