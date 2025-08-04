import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from google.cloud import aiplatform
from google.cloud.aiplatform import AutoMLTabularTrainingJob, Model, Endpoint
from google.cloud import storage
import joblib
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class VertexAIService:
    """Service for managing Vertex AI models and predictions."""

    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = settings.GCP_LOCATION
        self.bucket_name = settings.GCS_BUCKET_NAME

        # Initialize Vertex AI
        aiplatform.init(
            project=self.project_id,
            location=self.location,
            staging_bucket=f"gs://{self.bucket_name}/vertex-ai-staging",
        )

        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)

        # Model endpoints
        self.demand_model_endpoint: Optional[str] = None
        self.route_optimization_model_endpoint: Optional[str] = None
        self.churn_prediction_model_endpoint: Optional[str] = None

    async def train_demand_prediction_model(
        self, dataset_path: str, display_name: str = "lucky-gas-demand-prediction"
    ) -> str:
        """Train a demand prediction model using AutoML."""
        try:
            # Create AutoML training job
            job = AutoMLTabularTrainingJob(
                display_name=display_name,
                optimization_prediction_type="regression",
                optimization_objective="minimize-rmse",
                column_specs={
                    "customer_id": "categorical",
                    "day_of_week": "categorical",
                    "month": "categorical",
                    "cylinder_type": "categorical",
                    "weather_temp": "numeric",
                    "weather_humidity": "numeric",
                    "last_order_days": "numeric",
                    "avg_consumption": "numeric",
                    "is_holiday": "categorical",
                    "is_weekend": "categorical",
                },
            )

            # Run the training job
            model = job.run(
                dataset=dataset_path,
                target_column="demand_quantity",
                training_fraction_split=0.8,
                validation_fraction_split=0.1,
                test_fraction_split=0.1,
                model_display_name=f"{display_name}-model",
                budget_milli_node_hours=1000,  # 1 node hour for testing
            )

            logger.info(f"Model training completed: {model.resource_name}")
            return model.resource_name

        except Exception as e:
            logger.error(f"Error training demand prediction model: {str(e)}")
            raise

    async def deploy_model(
        self,
        model_name: str,
        endpoint_display_name: str,
        machine_type: str = "n1-standard-4",
    ) -> str:
        """Deploy a trained model to an endpoint."""
        try:
            # Get the model
            model = Model(model_name=model_name)

            # Create endpoint
            endpoint = Endpoint.create(
                display_name=endpoint_display_name,
                project=self.project_id,
                location=self.location,
            )

            # Deploy model to endpoint
            deployed_model = model.deploy(
                endpoint=endpoint,
                deployed_model_display_name=endpoint_display_name,
                machine_type=machine_type,
                min_replica_count=1,
                max_replica_count=3,
                accelerator_type=None,
                accelerator_count=0,
            )

            logger.info(f"Model deployed to endpoint: {endpoint.resource_name}")
            return endpoint.resource_name

        except Exception as e:
            logger.error(f"Error deploying model: {str(e)}")
            raise

    async def predict_daily_demand(
        self, customer_data: List[Dict[str, Any]], prediction_date: datetime
    ) -> List[Dict[str, Any]]:
        """Predict daily demand for customers."""
        try:
            if not self.demand_model_endpoint:
                raise ValueError("Demand model endpoint not configured")

            # Get endpoint
            endpoint = Endpoint(self.demand_model_endpoint)

            # Prepare instances for prediction
            instances = []
            for customer in customer_data:
                instance = {
                    "customer_id": customer["id"],
                    "day_of_week": prediction_date.strftime("%A"),
                    "month": str(prediction_date.month),
                    "cylinder_type": customer["cylinder_type"],
                    "weather_temp": await self._get_weather_temp(prediction_date),
                    "weather_humidity": await self._get_weather_humidity(
                        prediction_date
                    ),
                    "last_order_days": customer.get("days_since_last_order", 0),
                    "avg_consumption": customer.get("avg_consumption", 20),
                    "is_holiday": await self._is_holiday(prediction_date),
                    "is_weekend": prediction_date.weekday() >= 5,
                }
                instances.append(instance)

            # Make predictions
            predictions = endpoint.predict(instances=instances)

            # Format results
            results = []
            for i, prediction in enumerate(predictions.predictions):
                results.append(
                    {
                        "customer_id": customer_data[i]["id"],
                        "customer_name": customer_data[i]["name"],
                        "predicted_demand": round(prediction["value"], 2),
                        "confidence": prediction.get("confidence", 0.85),
                        "prediction_date": prediction_date.isoformat(),
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error predicting daily demand: {str(e)}")
            # Fallback to simple prediction
            return await self._fallback_demand_prediction(
                customer_data, prediction_date
            )

    async def optimize_routes(
        self,
        orders: List[Dict[str, Any]],
        drivers: List[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Optimize delivery routes using Vertex AI."""
        try:
            if not self.route_optimization_model_endpoint:
                # Use OR-Tools integration instead
                return await self._optimize_routes_with_ortools(
                    orders, drivers, constraints
                )

            endpoint = Endpoint(self.route_optimization_model_endpoint)

            # Prepare instance
            instance = {
                "orders": orders,
                "drivers": drivers,
                "constraints": constraints
                or {
                    "max_distance_per_route": 100,
                    "max_stops_per_route": 20,
                    "time_window_start": "08:00",
                    "time_window_end": "18:00",
                },
            }

            # Make prediction
            prediction = endpoint.predict(instances=[instance])

            return prediction.predictions[0]

        except Exception as e:
            logger.error(f"Error optimizing routes: {str(e)}")
            return await self._optimize_routes_with_ortools(
                orders, drivers, constraints
            )

    async def predict_customer_churn(
        self, customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict customer churn probability."""
        try:
            if not self.churn_prediction_model_endpoint:
                # Use simple heuristic
                return await self._simple_churn_prediction(customer_data)

            endpoint = Endpoint(self.churn_prediction_model_endpoint)

            # Prepare instance
            instance = {
                "days_since_last_order": customer_data.get("days_since_last_order", 0),
                "total_orders": customer_data.get("total_orders", 0),
                "avg_order_frequency": customer_data.get("avg_order_frequency", 30),
                "customer_type": customer_data.get("customer_type", "residential"),
                "payment_delays": customer_data.get("payment_delays", 0),
                "complaints": customer_data.get("complaints", 0),
            }

            # Make prediction
            prediction = endpoint.predict(instances=[instance])

            return {
                "customer_id": customer_data["id"],
                "churn_probability": prediction.predictions[0]["probability"],
                "risk_level": self._get_risk_level(
                    prediction.predictions[0]["probability"]
                ),
                "recommended_action": self._get_recommended_action(
                    prediction.predictions[0]["probability"]
                ),
            }

        except Exception as e:
            logger.error(f"Error predicting customer churn: {str(e)}")
            return await self._simple_churn_prediction(customer_data)

    async def batch_predict(
        self,
        input_uri: str,
        output_uri: str,
        model_endpoint: str,
        job_display_name: str,
    ) -> str:
        """Run batch prediction job."""
        try:
            model = Model(model_endpoint)

            batch_prediction_job = model.batch_predict(
                job_display_name=job_display_name,
                gcs_source=input_uri,
                gcs_destination_prefix=output_uri,
                machine_type="n1-standard-4",
                starting_replica_count=1,
                max_replica_count=5,
            )

            batch_prediction_job.wait()

            logger.info(
                f"Batch prediction completed: {batch_prediction_job.resource_name}"
            )
            return batch_prediction_job.resource_name

        except Exception as e:
            logger.error(f"Error running batch prediction: {str(e)}")
            raise

    # Helper methods
    async def _get_weather_temp(self, date: datetime) -> float:
        """Get weather temperature for prediction date."""
        # TODO: Integrate with weather API
        # For now, return seasonal average for Taipei
        month = date.month
        if month in [6, 7, 8]:  # Summer
            return 28.5
        elif month in [12, 1, 2]:  # Winter
            return 16.0
        else:  # Spring/Fall
            return 22.0

    async def _get_weather_humidity(self, date: datetime) -> float:
        """Get weather humidity for prediction date."""
        # TODO: Integrate with weather API
        # Taiwan average humidity
        return 75.0

    async def _is_holiday(self, date: datetime) -> str:
        """Check if date is a holiday in Taiwan."""
        # TODO: Integrate with Taiwan holiday calendar
        # For now, check weekends
        return "true" if date.weekday() >= 5 else "false"

    async def _fallback_demand_prediction(
        self, customer_data: List[Dict[str, Any]], prediction_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fallback demand prediction using simple heuristics."""
        results = []

        for customer in customer_data:
            # Simple prediction based on historical average
            avg_consumption = customer.get("avg_consumption", 20)
            days_since_last = customer.get("days_since_last_order", 0)

            # Increase probability as days increase
            probability = min(days_since_last / 30.0, 1.0)
            predicted_demand = avg_consumption * probability

            results.append(
                {
                    "customer_id": customer["id"],
                    "customer_name": customer["name"],
                    "predicted_demand": round(predicted_demand, 2),
                    "confidence": 0.7,  # Lower confidence for fallback
                    "prediction_date": prediction_date.isoformat(),
                }
            )

        return results

    async def _optimize_routes_with_ortools(
        self,
        orders: List[Dict[str, Any]],
        drivers: List[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Optimize routes using OR-Tools."""
        # This will be implemented in the routes service
        from app.services.route_optimization_service import RouteOptimizationService

        optimizer = RouteOptimizationService()
        return await optimizer.optimize_routes(orders, drivers, constraints)

    async def _simple_churn_prediction(
        self, customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simple churn prediction based on heuristics."""
        days_since_last = customer_data.get("days_since_last_order", 0)
        avg_frequency = customer_data.get("avg_order_frequency", 30)

        # Calculate churn probability
        if days_since_last > avg_frequency * 2:
            probability = 0.8
        elif days_since_last > avg_frequency * 1.5:
            probability = 0.6
        elif days_since_last > avg_frequency:
            probability = 0.4
        else:
            probability = 0.2

        return {
            "customer_id": customer_data["id"],
            "churn_probability": probability,
            "risk_level": self._get_risk_level(probability),
            "recommended_action": self._get_recommended_action(probability),
        }

    def _get_risk_level(self, probability: float) -> str:
        """Get risk level based on churn probability."""
        if probability >= 0.7:
            return "high"
        elif probability >= 0.4:
            return "medium"
        else:
            return "low"

    def _get_recommended_action(self, probability: float) -> str:
        """Get recommended action based on churn probability."""
        if probability >= 0.7:
            return "immediate_contact"
        elif probability >= 0.4:
            return "promotional_offer"
        else:
            return "monitor"

    async def upload_training_data(self, data: pd.DataFrame, dataset_name: str) -> str:
        """Upload training data to GCS for Vertex AI."""
        try:
            # Convert to CSV
            csv_data = data.to_csv(index=False)

            # Upload to GCS
            blob_name = f"vertex-ai-datasets/{dataset_name}/data.csv"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(csv_data, content_type="text/csv")

            logger.info(
                f"Training data uploaded to: gs://{self.bucket_name}/{blob_name}"
            )
            return f"gs://{self.bucket_name}/{blob_name}"

        except Exception as e:
            logger.error(f"Error uploading training data: {str(e)}")
            raise

    async def prepare_historical_data_for_training(self) -> pd.DataFrame:
        """Prepare historical data for model training."""
        # This would typically load from your database
        # For now, create sample data

        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        customers = [f"CUST{i:04d}" for i in range(1, 101)]

        data = []
        for date in dates:
            for customer in customers:
                data.append(
                    {
                        "customer_id": customer,
                        "date": date,
                        "day_of_week": date.strftime("%A"),
                        "month": str(date.month),
                        "cylinder_type": np.random.choice(["20kg", "16kg", "50kg"]),
                        "weather_temp": np.random.normal(22, 5),
                        "weather_humidity": np.random.normal(75, 10),
                        "last_order_days": np.random.randint(1, 60),
                        "avg_consumption": np.random.normal(20, 5),
                        "is_holiday": "true" if date.weekday() >= 5 else "false",
                        "is_weekend": date.weekday() >= 5,
                        "demand_quantity": np.random.normal(20, 5)
                        * (1 if date.weekday() < 5 else 1.2),
                    }
                )

        return pd.DataFrame(data)


# Singleton instance - lazy initialization
_vertex_ai_service = None


def get_vertex_ai_service():
    """Get or create the singleton vertex AI service"""
    global _vertex_ai_service
    if _vertex_ai_service is None:
        # Check if we're in development/testing mode
        import os

        if (
            os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
            or os.getenv("TESTING", "false").lower() == "true"
        ):
            # Return a mock service in development mode
            from app.services.google_cloud.mock_vertex_ai_service import (
                MockVertexAIDemandPredictionService,
            )

            return MockVertexAIDemandPredictionService()
        else:
            try:
                _vertex_ai_service = VertexAIService()
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Vertex AI service: {e}. Using mock service."
                )
                from app.services.google_cloud.mock_vertex_ai_service import (
                    MockVertexAIDemandPredictionService,
                )

                _vertex_ai_service = MockVertexAIDemandPredictionService()
    return _vertex_ai_service


# For backward compatibility - lazy initialization
# Don't initialize at module level to avoid credential issues
vertex_ai_service = None
