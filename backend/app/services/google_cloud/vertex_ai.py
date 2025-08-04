"""
Placeholder Vertex AI Service for demand prediction
This will be replaced with actual Google Cloud Vertex AI implementation
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_async_session
from app.models.customer import Customer
from app.models.delivery import DeliveryPrediction

logger = logging.getLogger(__name__)


class DemandPredictionService:
    """
    Placeholder service for demand prediction using mock data
    In production, this will use Google Cloud Vertex AI AutoML
    """

    def __init__(self):
        self.project_id = (
            settings.GCP_PROJECT_ID
            if hasattr(settings, "GCP_PROJECT_ID")
            else "placeholder-project"
        )
        self.location = (
            settings.GCP_LOCATION if hasattr(settings, "GCP_LOCATION") else "asia-east1"
        )
        self.model_id = "placeholder-model-v1"

    async def train_demand_model(self) -> Dict[str, Any]:
        """
        Placeholder for training demand prediction model
        In production, this will create and train a Vertex AI AutoML model
        """
        logger.info("Starting placeholder model training...")

        # Simulate training time
        await asyncio.sleep(2)

        return {
            "model_id": self.model_id,
            "model_name": "demand_predictor_v1",
            "status": "trained",
            "accuracy": 0.85,
            "created_at": datetime.utcnow().isoformat(),
            "training_hours": 2.5,
            "features_used": [
                "historical_consumption",
                "cylinder_sizes",
                "delivery_frequency",
                "seasonal_patterns",
                "customer_type",
            ],
        }

    async def predict_demand_batch(self) -> Dict[str, Any]:
        """
        Generate batch predictions for all active customers
        Returns mock predictions based on customer patterns
        """
        logger.info("Generating batch demand predictions...")

        predictions_created = 0
        predictions_data = []

        async for session in get_async_session():
            # Get all active customers
            result = await session.execute(
                select(Customer).where(Customer.is_active == True)
            )
            customers = result.scalars().all()

            for customer in customers:
                # Generate mock prediction based on customer data
                prediction_data = await self._generate_customer_prediction(customer)
                predictions_data.append(prediction_data)

                # Create prediction record
                prediction = DeliveryPrediction(
                    customer_id=customer.id,
                    predicted_date=datetime.combine(
                        prediction_data["predicted_date"], datetime.min.time()
                    ),
                    predicted_quantity_50kg=prediction_data["quantities"]["50kg"],
                    predicted_quantity_20kg=prediction_data["quantities"]["20kg"],
                    predicted_quantity_16kg=prediction_data["quantities"]["16kg"],
                    predicted_quantity_10kg=prediction_data["quantities"]["10kg"],
                    predicted_quantity_4kg=prediction_data["quantities"]["4kg"],
                    confidence_score=prediction_data["confidence_score"],
                    model_version=self.model_id,
                    factors_json=json.dumps(
                        {
                            "avg_consumption": prediction_data["avg_consumption"],
                            "days_since_last": prediction_data["days_since_last"],
                            "seasonal_factor": prediction_data["seasonal_factor"],
                        }
                    ),
                )
                session.add(prediction)
                predictions_created += 1

            await session.commit()

        return {
            "batch_id": f"batch-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "predictions_count": predictions_created,
            "model_version": self.model_id,
            "execution_time_seconds": 5.2,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "urgent_deliveries": len(
                    [p for p in predictions_data if p["is_urgent"]]
                ),
                "total_50kg": sum(p["quantities"]["50kg"] for p in predictions_data),
                "total_20kg": sum(p["quantities"]["20kg"] for p in predictions_data),
                "average_confidence": (
                    sum(p["confidence_score"] for p in predictions_data)
                    / len(predictions_data)
                    if predictions_data
                    else 0
                ),
            },
        }

    async def _generate_customer_prediction(self, customer: Customer) -> Dict[str, Any]:
        """
        Generate mock prediction for a single customer
        Based on their historical patterns and cylinder inventory
        """
        # Base consumption rates (cylinders per month)
        base_rates = {"50kg": 0.5, "20kg": 1.0, "16kg": 1.2, "10kg": 2.0, "4kg": 3.0}

        # Adjust based on customer inventory
        monthly_consumption = {
            "50kg": base_rates["50kg"] * (1 if customer.cylinders_50kg > 0 else 0),
            "20kg": base_rates["20kg"] * (1 if customer.cylinders_20kg > 0 else 0),
            "16kg": base_rates["16kg"] * (1 if customer.cylinders_16kg > 0 else 0),
            "10kg": base_rates["10kg"] * (1 if customer.cylinders_10kg > 0 else 0),
            "4kg": base_rates["4kg"] * (1 if customer.cylinders_4kg > 0 else 0),
        }

        # Add randomness for realistic variation
        for size in monthly_consumption:
            monthly_consumption[size] *= random.uniform(0.8, 1.2)

        # Calculate days until next order
        days_since_last = random.randint(15, 45)  # Mock data
        days_until_next = max(1, 30 - days_since_last + random.randint(-5, 5))

        # Seasonal factor (higher in winter)
        month = datetime.utcnow().month
        seasonal_factor = 1.3 if month in [12, 1, 2] else 1.0

        # Calculate predicted quantities
        predicted_quantities = {
            "50kg": round(monthly_consumption["50kg"] * seasonal_factor),
            "20kg": round(monthly_consumption["20kg"] * seasonal_factor),
            "16kg": round(monthly_consumption["16kg"] * seasonal_factor),
            "10kg": round(monthly_consumption["10kg"] * seasonal_factor),
            "4kg": round(monthly_consumption["4kg"] * seasonal_factor),
        }

        # Confidence score based on customer history
        confidence_score = random.uniform(0.75, 0.95)

        # Determine if urgent
        is_urgent = days_until_next <= 3

        return {
            "customer_id": customer.id,
            "predicted_date": (
                datetime.utcnow() + timedelta(days=days_until_next)
            ).date(),
            "quantities": predicted_quantities,
            "confidence_score": confidence_score,
            "is_urgent": is_urgent,
            "avg_consumption": sum(monthly_consumption.values()),
            "days_since_last": days_since_last,
            "seasonal_factor": seasonal_factor,
        }

    async def get_customer_prediction(
        self, customer_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest prediction for a specific customer
        """
        async for session in get_async_session():
            result = await session.execute(
                select(DeliveryPrediction)
                .where(DeliveryPrediction.customer_id == customer_id)
                .order_by(DeliveryPrediction.created_at.desc())
                .limit(1)
            )
            prediction = result.scalar_one_or_none()

            if prediction:
                return {
                    "customer_id": prediction.customer_id,
                    "predicted_date": prediction.predicted_date.isoformat(),
                    "quantities": {
                        "50kg": prediction.predicted_quantity_50kg,
                        "20kg": prediction.predicted_quantity_20kg,
                        "16kg": prediction.predicted_quantity_16kg,
                        "10kg": prediction.predicted_quantity_10kg,
                        "4kg": prediction.predicted_quantity_4kg,
                    },
                    "confidence_score": prediction.confidence_score,
                    "model_version": prediction.model_version,
                    "created_at": prediction.created_at.isoformat(),
                }

            return None

    async def get_prediction_metrics(self) -> Dict[str, Any]:
        """
        Get prediction performance metrics
        """
        # Mock metrics for demonstration
        return {
            "model_id": self.model_id,
            "accuracy_metrics": {
                "mae": 2.3,  # Mean Absolute Error
                "rmse": 3.1,  # Root Mean Square Error
                "mape": 0.12,  # Mean Absolute Percentage Error
            },
            "feature_importance": {
                "historical_consumption": 0.35,
                "days_since_last_order": 0.25,
                "seasonal_patterns": 0.20,
                "cylinder_inventory": 0.15,
                "customer_type": 0.05,
            },
            "last_training_date": datetime.utcnow().date().isoformat(),
            "predictions_generated_today": random.randint(50, 150),
            "model_status": "healthy",
        }


# Singleton instance
demand_prediction_service = DemandPredictionService()
