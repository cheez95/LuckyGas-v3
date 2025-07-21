"""
Enhanced Google Cloud Vertex AI Service with comprehensive monitoring and protection
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from google.cloud import aiplatform
from google.cloud.aiplatform import TabularDataset, AutoMLTabularTrainingJob, Model
from google.cloud import storage
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.google_cloud_config import get_gcp_config
from app.core.database import get_async_session
from app.models.customer import Customer
from app.models.delivery import DeliveryPrediction, DeliveryHistory
from app.models.order import Order
from app.services.google_cloud.vertex_ai_service import VertexAIDemandPredictionService
from app.services.google_cloud.monitoring.rate_limiter import GoogleAPIRateLimiter
from app.services.google_cloud.monitoring.cost_monitor import GoogleAPICostMonitor
from app.services.google_cloud.monitoring.error_handler import GoogleAPIErrorHandler
from app.services.google_cloud.monitoring.circuit_breaker import CircuitBreaker
from app.services.google_cloud.monitoring.api_cache import GoogleAPICache
from app.services.google_cloud.development_mode import DevelopmentModeManager
from app.services.google_cloud.mock_vertex_ai_service import MockVertexAIDemandPredictionService
from app.core.security.api_key_manager import get_api_key_manager

logger = logging.getLogger(__name__)


class EnhancedVertexAIService(VertexAIDemandPredictionService):
    """
    Enhanced Vertex AI service with comprehensive monitoring, security, and resilience features
    """
    
    def __init__(self):
        """Initialize enhanced service with all monitoring components"""
        super().__init__()
        
        # Initialize monitoring components
        self.rate_limiter = GoogleAPIRateLimiter()
        self.cost_monitor = GoogleAPICostMonitor()
        self.error_handler = GoogleAPIErrorHandler()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            half_open_retries=3
        )
        self.cache = GoogleAPICache()
        self.key_manager = None  # Will be initialized asynchronously
        self.dev_mode_manager = DevelopmentModeManager()
        self.mock_service = MockVertexAIDemandPredictionService()
        
        # Track service metrics
        self.metrics = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "cache_hits": 0,
            "total_training_jobs": 0,
            "successful_training_jobs": 0
        }
    
    async def _ensure_key_manager(self):
        """Ensure API key manager is initialized"""
        if not self.key_manager:
            self.key_manager = await get_api_key_manager()
    
    async def _get_api_key(self) -> Optional[str]:
        """Get Vertex AI API key securely"""
        await self._ensure_key_manager()
        return await self.key_manager.get_key("vertex_ai")
    
    async def initialize_endpoint(self):
        """Initialize Vertex AI endpoint with monitoring"""
        # Check development mode
        mode = await self.dev_mode_manager.detect_mode()
        if mode == self.dev_mode_manager.development_mode.DEVELOPMENT:
            logger.info("Using mock Vertex AI service in development mode")
            return
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            logger.warning("Circuit breaker is OPEN for Vertex AI")
            return
        
        try:
            # Call parent initialization
            await super().initialize_endpoint()
            self.circuit_breaker.record_success()
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Failed to initialize Vertex AI endpoint: {e}")
            raise
    
    async def train_demand_model(self) -> Dict[str, Any]:
        """
        Train a new demand prediction model with comprehensive monitoring
        """
        operation_id = f"train_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Check development mode
        mode = await self.dev_mode_manager.detect_mode()
        if mode == self.dev_mode_manager.development_mode.DEVELOPMENT:
            logger.info("Using mock model training in development mode")
            return {
                "model_id": "mock_model_123",
                "endpoint_id": "mock_endpoint_123",
                "model_name": "mock_demand_predictor",
                "status": "trained_and_deployed",
                "created_at": datetime.utcnow().isoformat(),
                "training_hours": 0.5,
                "features_used": [
                    "avg_daily_usage",
                    "days_since_last_order",
                    "cylinder_inventory",
                    "customer_type",
                    "area",
                    "temporal_features"
                ]
            }
        
        # Check rate limit
        if not await self.rate_limiter.check_limit("vertex_ai"):
            raise Exception("Vertex AI API rate limit exceeded")
        
        # Check cost budget
        estimated_cost = 50.0  # Estimated training cost
        if not await self.cost_monitor.check_budget("vertex_ai", estimated_cost):
            raise Exception("Vertex AI cost budget exceeded")
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise Exception("Circuit breaker is OPEN for Vertex AI")
        
        # Execute with error handling
        result = await self.error_handler.execute_with_retry(
            self._train_model_internal,
            operation_id=operation_id
        )
        
        # Track metrics
        self.metrics["total_training_jobs"] += 1
        if result.get("status") == "trained_and_deployed":
            self.metrics["successful_training_jobs"] += 1
            
            # Track actual cost
            await self.cost_monitor.track_cost(
                "vertex_ai",
                "model_training",
                estimated_cost,
                {"model_id": result.get("model_id")}
            )
        
        return result
    
    async def _train_model_internal(self) -> Dict[str, Any]:
        """Internal training method wrapped by monitoring"""
        try:
            result = await super().train_demand_model()
            self.circuit_breaker.record_success()
            return result
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
    
    async def predict_demand_batch(self) -> Dict[str, Any]:
        """
        Generate batch predictions with comprehensive monitoring and caching
        """
        operation_id = f"batch_predict_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Check development mode
        mode = await self.dev_mode_manager.detect_mode()
        if mode == self.dev_mode_manager.development_mode.DEVELOPMENT:
            logger.info("Using mock predictions in development mode")
            return await self.mock_service.predict_demand_batch()
        
        # Check cache first
        cache_key = f"batch_predictions_{datetime.now().strftime('%Y%m%d')}"
        cached_result = await self.cache.get(cache_key, "vertex_ai")
        if cached_result:
            self.metrics["cache_hits"] += 1
            logger.info(f"Returning cached batch predictions: {cache_key}")
            return cached_result
        
        # Check rate limit
        if not await self.rate_limiter.check_limit("vertex_ai"):
            # Fall back to cached or mock predictions
            logger.warning("Rate limit exceeded, using mock predictions")
            return await self.mock_service.predict_demand_batch()
        
        # Check cost budget
        estimated_cost = 0.05 * 100  # $0.05 per prediction * estimated count
        if not await self.cost_monitor.check_budget("vertex_ai", estimated_cost):
            logger.warning("Cost budget exceeded, using mock predictions")
            return await self.mock_service.predict_demand_batch()
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            logger.warning("Circuit breaker OPEN, using mock predictions")
            return await self.mock_service.predict_demand_batch()
        
        # Execute with error handling
        self.metrics["total_predictions"] += 1
        
        try:
            result = await self.error_handler.execute_with_retry(
                self._predict_batch_internal,
                operation_id=operation_id
            )
            
            # Cache successful result
            if result.get("predictions_count", 0) > 0:
                await self.cache.set(
                    cache_key,
                    result,
                    "vertex_ai",
                    ttl=3600  # Cache for 1 hour
                )
                self.metrics["successful_predictions"] += 1
                
                # Track actual cost
                actual_cost = 0.05 * result.get("predictions_count", 0)
                await self.cost_monitor.track_cost(
                    "vertex_ai",
                    "batch_prediction",
                    actual_cost,
                    {"batch_id": result.get("batch_id")}
                )
            
            return result
            
        except Exception as e:
            self.metrics["failed_predictions"] += 1
            logger.error(f"Batch prediction failed: {e}, using mock predictions")
            return await self.mock_service.predict_demand_batch()
    
    async def _predict_batch_internal(self) -> Dict[str, Any]:
        """Internal prediction method wrapped by monitoring"""
        try:
            result = await super().predict_demand_batch()
            self.circuit_breaker.record_success()
            return result
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
    
    async def get_customer_prediction(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get prediction for specific customer with caching"""
        # Check development mode
        mode = await self.dev_mode_manager.detect_mode()
        if mode == self.dev_mode_manager.development_mode.DEVELOPMENT:
            return await self.mock_service.get_customer_prediction(customer_id)
        
        # Check cache
        cache_key = f"prediction_customer_{customer_id}_{datetime.now().strftime('%Y%m%d')}"
        cached_result = await self.cache.get(cache_key, "vertex_ai")
        if cached_result:
            self.metrics["cache_hits"] += 1
            return cached_result
        
        # Get prediction
        result = await super().get_customer_prediction(customer_id)
        
        # Cache result
        if result:
            await self.cache.set(
                cache_key,
                result,
                "vertex_ai",
                ttl=3600  # Cache for 1 hour
            )
        
        return result
    
    async def get_prediction_metrics(self) -> Dict[str, Any]:
        """Get enhanced prediction metrics including monitoring data"""
        base_metrics = await super().get_prediction_metrics()
        
        # Add monitoring metrics
        monitoring_metrics = {
            "monitoring_stats": {
                "total_predictions": self.metrics["total_predictions"],
                "successful_predictions": self.metrics["successful_predictions"],
                "failed_predictions": self.metrics["failed_predictions"],
                "success_rate": (
                    self.metrics["successful_predictions"] / self.metrics["total_predictions"]
                    if self.metrics["total_predictions"] > 0 else 0
                ),
                "cache_hit_rate": (
                    self.metrics["cache_hits"] / self.metrics["total_predictions"]
                    if self.metrics["total_predictions"] > 0 else 0
                ),
                "total_training_jobs": self.metrics["total_training_jobs"],
                "successful_training_jobs": self.metrics["successful_training_jobs"]
            },
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "rate_limit_status": await self.rate_limiter.get_current_usage("vertex_ai"),
            "cost_status": await self.cost_monitor.get_api_usage("vertex_ai")
        }
        
        return {**base_metrics, **monitoring_metrics}
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for Vertex AI service"""
        health_status = {
            "service": "vertex_ai",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check circuit breaker
        cb_status = self.circuit_breaker.get_status()
        health_status["components"]["circuit_breaker"] = {
            "status": "healthy" if cb_status["state"] != "OPEN" else "unhealthy",
            "details": cb_status
        }
        
        # Check rate limiter
        rate_status = await self.rate_limiter.get_current_usage("vertex_ai")
        health_status["components"]["rate_limiter"] = {
            "status": "healthy" if rate_status["available"] else "throttled",
            "details": rate_status
        }
        
        # Check cost monitor
        cost_status = await self.cost_monitor.get_api_usage("vertex_ai")
        health_status["components"]["cost_monitor"] = {
            "status": "healthy" if not cost_status["over_budget"] else "over_budget",
            "details": cost_status
        }
        
        # Check endpoint connectivity
        try:
            if self.endpoint or self.model:
                health_status["components"]["endpoint"] = {
                    "status": "connected",
                    "endpoint_id": self.gcp_config.vertex_endpoint_id,
                    "model_id": self.gcp_config.vertex_model_id
                }
            else:
                health_status["components"]["endpoint"] = {
                    "status": "not_initialized"
                }
        except Exception as e:
            health_status["components"]["endpoint"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Overall status
        unhealthy_components = [
            comp for comp, details in health_status["components"].items()
            if details.get("status") not in ["healthy", "connected"]
        ]
        
        if unhealthy_components:
            health_status["status"] = "degraded"
            health_status["unhealthy_components"] = unhealthy_components
        
        return health_status


# Create singleton instance
enhanced_vertex_ai_service = EnhancedVertexAIService()