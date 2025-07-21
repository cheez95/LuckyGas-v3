"""
Mock Vertex AI Service for Development

Provides realistic mock predictions for development and testing.
"""
import random
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, date
import logging
import numpy as np
from math import sin, cos, pi

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, date
import logging
import random
import asyncio
import json
import numpy as np
from math import sin, cos, pi
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.customer import Customer
from app.models.delivery import DeliveryPrediction
from app.core.config import settings
from app.models.order import Order
from app.models.customer import Customer
from app.core.config import settings

logger = logging.getLogger(__name__)


class MockVertexAIDemandPredictionService:
    """
    Mock implementation of Vertex AI for development
    Provides deterministic predictions for testing
    """
    
    def __init__(self):
        # Don't call parent __init__ to avoid API initialization
        self.model_name = "mock-vertex-ai-model"
        self.mock_delays = {
            "min": 0.05,  # 50ms minimum
            "max": 0.3    # 300ms maximum
        }
        
        # Taiwan-specific patterns
        self.seasonal_factors = {
            1: 1.2,   # January - New Year, cold weather
            2: 1.1,   # February - Chinese New Year
            3: 0.9,   # March - Spring
            4: 0.85,  # April - Spring
            5: 0.8,   # May - Getting warmer
            6: 0.7,   # June - Summer begins
            7: 0.65,  # July - Hot summer
            8: 0.65,  # August - Hot summer
            9: 0.75,  # September - Still warm
            10: 0.85, # October - Cooling down
            11: 0.95, # November - Getting cooler
            12: 1.15  # December - Cold weather
        }
        
        self.day_of_week_factors = {
            0: 1.1,   # Monday
            1: 1.0,   # Tuesday
            2: 1.0,   # Wednesday
            3: 1.05,  # Thursday
            4: 1.15,  # Friday - Weekend prep
            5: 1.2,   # Saturday - Weekend
            6: 0.9    # Sunday - Lower demand
        }
        
        # Area-specific demand patterns
        self.area_base_demand = {
            "信義區": {"base": 150, "volatility": 0.15},
            "大安區": {"base": 120, "volatility": 0.12},
            "中山區": {"base": 110, "volatility": 0.13},
            "松山區": {"base": 100, "volatility": 0.11},
            "內湖區": {"base": 90, "volatility": 0.14},
            "士林區": {"base": 95, "volatility": 0.12},
            "北投區": {"base": 85, "volatility": 0.13},
            "文山區": {"base": 80, "volatility": 0.15},
            "南港區": {"base": 75, "volatility": 0.16},
            "萬華區": {"base": 105, "volatility": 0.14},
            "中正區": {"base": 115, "volatility": 0.12},
            "大同區": {"base": 100, "volatility": 0.13}
        }
        
        # Product demand distribution
        self.product_distribution = {
            "50kg": 0.35,  # Commercial use
            "20kg": 0.30,  # Large households
            "16kg": 0.20,  # Medium households
            "10kg": 0.10,  # Small households
            "4kg": 0.05    # Portable/camping
        }
    
    async def initialize_endpoint(self):
        """Mock endpoint initialization"""
        logger.info("Mock Vertex AI endpoint initialized")
        self.endpoint = "mock-endpoint"
        self.model = "mock-model"
    
    async def predict_daily_demand(
        self,
        prediction_date: date,
        area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate mock daily demand predictions
        """
        # Simulate API latency
        delay = random.uniform(self.mock_delays["min"], self.mock_delays["max"])
        await asyncio.sleep(delay)
        
        logger.info(f"Mock demand prediction for {prediction_date} (area: {area or 'all'})")
        
        # Calculate base demand factors
        month_factor = self.seasonal_factors.get(prediction_date.month, 1.0)
        dow_factor = self.day_of_week_factors.get(prediction_date.weekday(), 1.0)
        
        # Weather simulation (temperature affects gas demand)
        temp_adjustment = self._simulate_temperature_effect(prediction_date)
        
        # Holiday adjustments
        holiday_factor = self._get_holiday_factor(prediction_date)
        
        predictions = {}
        
        if area:
            # Single area prediction
            predictions[area] = self._generate_area_prediction(
                area, prediction_date, month_factor, dow_factor, 
                temp_adjustment, holiday_factor
            )
        else:
            # All areas prediction
            for area_name in self.area_base_demand.keys():
                predictions[area_name] = self._generate_area_prediction(
                    area_name, prediction_date, month_factor, dow_factor,
                    temp_adjustment, holiday_factor
                )
        
        # Add aggregate statistics
        total_predicted = sum(p["total_cylinders"] for p in predictions.values())
        
        return {
            "prediction_date": prediction_date.isoformat(),
            "model_version": "mock-v1.0",
            "confidence_score": round(0.75 + random.uniform(0, 0.15), 3),
            "predictions_by_area": predictions,
            "total_predicted_demand": total_predicted,
            "factors_applied": {
                "seasonal": round(month_factor, 2),
                "day_of_week": round(dow_factor, 2),
                "temperature": round(temp_adjustment, 2),
                "holiday": round(holiday_factor, 2)
            },
            "warnings": ["Using mock prediction service (development mode)"]
        }
    
    def _generate_area_prediction(
        self,
        area: str,
        prediction_date: date,
        month_factor: float,
        dow_factor: float,
        temp_adjustment: float,
        holiday_factor: float
    ) -> Dict[str, Any]:
        """Generate prediction for a specific area"""
        area_info = self.area_base_demand.get(area, {"base": 100, "volatility": 0.15})
        base_demand = area_info["base"]
        volatility = area_info["volatility"]
        
        # Calculate total demand with all factors
        total_factor = month_factor * dow_factor * temp_adjustment * holiday_factor
        
        # Add some randomness based on volatility
        random_factor = 1 + random.gauss(0, volatility)
        
        # Calculate final demand
        total_demand = int(base_demand * total_factor * random_factor)
        total_demand = max(20, total_demand)  # Minimum demand
        
        # Distribute among products
        product_demands = {}
        remaining = total_demand
        
        for product, distribution in self.product_distribution.items():
            if product == "4kg":  # Last one gets remainder
                product_demands[product] = remaining
            else:
                qty = int(total_demand * distribution)
                product_demands[product] = qty
                remaining -= qty
        
        # Add time-based patterns
        peak_hours = [10, 11, 14, 15, 16, 17]  # Business hours
        hourly_distribution = self._generate_hourly_distribution(peak_hours)
        
        return {
            "area": area,
            "total_cylinders": total_demand,
            "products": product_demands,
            "confidence": round(0.7 + random.uniform(0, 0.2), 2),
            "peak_hours": peak_hours,
            "hourly_distribution": hourly_distribution,
            "historical_comparison": {
                "vs_last_week": round(random.uniform(-0.1, 0.1), 3),
                "vs_last_month": round(random.uniform(-0.15, 0.15), 3),
                "vs_last_year": round(random.uniform(-0.2, 0.2), 3)
            }
        }
    
    def _simulate_temperature_effect(self, prediction_date: date) -> float:
        """Simulate temperature effect on gas demand"""
        # Simple sinusoidal temperature model
        day_of_year = prediction_date.timetuple().tm_yday
        
        # Taiwan temperature range: 15°C (winter) to 30°C (summer)
        # Peak cold around day 30 (end of January)
        # Peak hot around day 210 (end of July)
        
        temp_celsius = 22.5 + 7.5 * sin((day_of_year - 30) * 2 * pi / 365)
        
        # Gas demand increases when cold
        if temp_celsius < 20:
            return 1 + (20 - temp_celsius) * 0.03  # 3% increase per degree below 20°C
        elif temp_celsius > 25:
            return 1 - (temp_celsius - 25) * 0.01  # 1% decrease per degree above 25°C
        else:
            return 1.0
    
    def _get_holiday_factor(self, prediction_date: date) -> float:
        """Check for Taiwan holidays and adjust demand"""
        # Major Taiwan holidays (simplified)
        holidays = {
            (1, 1): 1.3,    # New Year's Day
            (2, 14): 1.2,   # Approximate Chinese New Year
            (2, 28): 1.1,   # 228 Peace Memorial Day
            (4, 4): 1.1,    # Children's Day
            (4, 5): 1.1,    # Tomb Sweeping Day
            (5, 1): 1.05,   # Labor Day
            (10, 10): 1.15, # Double Tenth Day
            (12, 25): 1.1   # Christmas (westernized)
        }
        
        holiday_key = (prediction_date.month, prediction_date.day)
        return holidays.get(holiday_key, 1.0)
    
    def _generate_hourly_distribution(self, peak_hours: List[int]) -> Dict[int, float]:
        """Generate hourly demand distribution"""
        distribution = {}
        total = 0
        
        for hour in range(24):
            if hour in peak_hours:
                # Peak hour demand
                demand = 0.08 + random.uniform(0, 0.02)
            elif 6 <= hour <= 21:
                # Normal business hours
                demand = 0.04 + random.uniform(0, 0.01)
            else:
                # Night hours
                demand = 0.01 + random.uniform(0, 0.005)
            
            distribution[hour] = round(demand, 3)
            total += demand
        
        # Normalize to sum to 1
        for hour in distribution:
            distribution[hour] = round(distribution[hour] / total, 3)
        
        return distribution
    
    async def predict_customer_churn(
        self,
        customer_id: int,
        lookback_days: int = 90
    ) -> Dict[str, Any]:
        """
        Generate mock customer churn prediction
        """
        # Simulate API latency
        delay = random.uniform(self.mock_delays["min"], self.mock_delays["max"])
        await asyncio.sleep(delay)
        
        logger.info(f"Mock churn prediction for customer {customer_id}")
        
        # Generate mock churn probability based on customer ID
        # Use customer_id as seed for consistent results
        random.seed(customer_id)
        
        # Base churn probability
        base_churn = random.uniform(0.05, 0.25)
        
        # Risk factors
        risk_factors = {
            "decreasing_order_frequency": random.choice([True, False]),
            "reduced_order_size": random.choice([True, False]),
            "increased_complaints": random.choice([True, False]),
            "payment_delays": random.choice([True, False]),
            "competitor_activity": random.choice([True, False])
        }
        
        # Adjust churn probability based on risk factors
        churn_probability = base_churn
        for factor, present in risk_factors.items():
            if present:
                churn_probability *= 1.3
        
        churn_probability = min(0.95, churn_probability)  # Cap at 95%
        
        # Generate recommendations
        recommendations = []
        if churn_probability > 0.7:
            recommendations = [
                "立即聯繫客戶了解需求",
                "提供特別優惠或折扣",
                "安排客戶經理拜訪"
            ]
        elif churn_probability > 0.4:
            recommendations = [
                "增加客戶互動頻率",
                "提供更好的服務",
                "調查客戶滿意度"
            ]
        else:
            recommendations = [
                "維持現有服務水準",
                "定期關懷客戶"
            ]
        
        # Reset random seed
        random.seed()
        
        return {
            "customer_id": customer_id,
            "churn_probability": round(churn_probability, 3),
            "risk_level": self._get_risk_level(churn_probability),
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "confidence_score": round(0.7 + random.uniform(0, 0.2), 3),
            "model_version": "mock-churn-v1.0",
            "prediction_date": datetime.now().isoformat(),
            "warnings": ["Using mock prediction service (development mode)"]
        }
    
    def _get_risk_level(self, churn_probability: float) -> str:
        """Categorize risk level based on churn probability"""
        if churn_probability >= 0.7:
            return "high"
        elif churn_probability >= 0.4:
            return "medium"
        else:
            return "low"
    
    async def optimize_delivery_schedule(
        self,
        orders: List[Order],
        constraints: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate mock delivery schedule optimization
        """
        # Simulate API latency
        delay = random.uniform(0.1, 0.3)
        await asyncio.sleep(delay)
        
        logger.info(f"Mock delivery optimization for {len(orders)} orders")
        
        # Group orders by area
        area_orders = {}
        for order in orders:
            if order.customer and order.customer.area:
                area = order.customer.area
                if area not in area_orders:
                    area_orders[area] = []
                area_orders[area].append(order)
        
        # Generate optimized schedule
        optimized_routes = []
        total_distance_saved = 0
        
        for area, area_order_list in area_orders.items():
            # Create mock route
            route = {
                "area": area,
                "orders": [order.id for order in area_order_list],
                "estimated_duration_minutes": len(area_order_list) * 15 + 30,
                "estimated_distance_km": len(area_order_list) * 2.5 + 10,
                "optimization_score": round(0.7 + random.uniform(0, 0.2), 2),
                "vehicle_utilization": round(0.6 + random.uniform(0, 0.3), 2)
            }
            optimized_routes.append(route)
            
            # Mock distance savings
            original_distance = route["estimated_distance_km"] * 1.3
            total_distance_saved += original_distance - route["estimated_distance_km"]
        
        return {
            "optimization_id": f"mock-opt-{datetime.now().timestamp()}",
            "optimized_routes": optimized_routes,
            "total_routes": len(optimized_routes),
            "total_orders": len(orders),
            "metrics": {
                "total_distance_km": sum(r["estimated_distance_km"] for r in optimized_routes),
                "total_duration_minutes": sum(r["estimated_duration_minutes"] for r in optimized_routes),
                "distance_saved_km": round(total_distance_saved, 1),
                "optimization_score": round(0.75 + random.uniform(0, 0.15), 2)
            },
            "warnings": ["Using mock optimization service (development mode)"]
        }
    
    async def analyze_demand_patterns(
        self,
        start_date: date,
        end_date: date,
        area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate mock demand pattern analysis
        """
        # Simulate API latency
        delay = random.uniform(self.mock_delays["min"], self.mock_delays["max"])
        await asyncio.sleep(delay)
        
        logger.info(f"Mock demand analysis from {start_date} to {end_date}")
        
        # Generate trend data
        num_days = (end_date - start_date).days + 1
        dates = [start_date + timedelta(days=i) for i in range(num_days)]
        
        # Generate mock time series
        trend_data = []
        for date in dates:
            month_factor = self.seasonal_factors.get(date.month, 1.0)
            dow_factor = self.day_of_week_factors.get(date.weekday(), 1.0)
            base_demand = 1000 if not area else self.area_base_demand.get(area, {"base": 100})["base"]
            
            daily_demand = int(base_demand * month_factor * dow_factor * random.uniform(0.9, 1.1))
            
            trend_data.append({
                "date": date.isoformat(),
                "demand": daily_demand,
                "day_of_week": date.strftime("%A"),
                "is_holiday": random.choice([False, False, False, True])  # 25% chance
            })
        
        # Identify patterns
        patterns = {
            "weekly_pattern": {
                "peak_days": ["Friday", "Saturday"],
                "low_days": ["Sunday", "Monday"],
                "variation": "±15%"
            },
            "seasonal_trend": {
                "direction": "increasing" if end_date.month > start_date.month else "stable",
                "strength": "moderate"
            },
            "anomalies_detected": random.randint(0, 3)
        }
        
        # Generate insights
        insights = [
            "週五和週六的需求量最高，建議增加庫存",
            "冬季需求量比夏季高約30%",
            "節假日需求量平均增加20%"
        ]
        
        return {
            "analysis_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": num_days
            },
            "area": area or "all",
            "trend_data": trend_data,
            "patterns": patterns,
            "insights": insights,
            "statistics": {
                "average_daily_demand": sum(d["demand"] for d in trend_data) / len(trend_data),
                "peak_demand": max(d["demand"] for d in trend_data),
                "minimum_demand": min(d["demand"] for d in trend_data),
                "standard_deviation": 150  # Mock value
            },
            "model_version": "mock-analysis-v1.0",
            "warnings": ["Using mock analysis service (development mode)"]
        }
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the mock model"""
        return {
            "model_name": self.model_name,
            "model_type": "mock",
            "version": "1.0.0",
            "status": "healthy",
            "is_mock": True,
            "capabilities": [
                "daily_demand_prediction",
                "customer_churn_prediction",
                "delivery_optimization",
                "demand_pattern_analysis"
            ],
            "warnings": ["This is a mock service for development. Results are simulated."]
        }
    
    async def predict_demand_batch(self) -> Dict[str, Any]:
        """
        Generate batch predictions for all active customers (mock)
        """
        # Simulate API latency
        delay = random.uniform(0.1, 0.3)
        await asyncio.sleep(delay)
        
        logger.info("Mock batch demand prediction")
        
        # Mock batch prediction results
        predictions_count = random.randint(50, 200)
        urgent_count = int(predictions_count * 0.15)  # 15% urgent
        
        return {
            "batch_id": f"mock-batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "predictions_count": predictions_count,
            "model_version": "mock-model-v1.0",
            "execution_time_seconds": round(delay + random.uniform(5, 15), 2),
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "urgent_deliveries": urgent_count,
                "total_50kg": predictions_count * 2,
                "total_20kg": predictions_count * 3,
                "average_confidence": 0.82
            },
            "warnings": ["Using mock prediction service (development mode)"]
        }
    
    async def get_customer_prediction(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the latest prediction for a specific customer (mock)
        """
        # Simulate API latency
        delay = random.uniform(0.05, 0.15)
        await asyncio.sleep(delay)
        
        # Generate consistent prediction based on customer ID
        random.seed(customer_id)
        days_until_next = random.randint(3, 30)
        
        # Reset random seed
        random.seed()
        
        predicted_date = datetime.now() + timedelta(days=days_until_next)
        
        return {
            "customer_id": customer_id,
            "predicted_date": predicted_date.isoformat(),
            "days_until_delivery": days_until_next,
            "is_urgent": days_until_next <= 5,
            "predicted_quantities": {
                "50kg": random.randint(0, 3),
                "20kg": random.randint(0, 5),
                "16kg": random.randint(0, 4),
                "10kg": random.randint(0, 2),
                "4kg": random.randint(0, 1)
            },
            "confidence_score": round(0.7 + random.uniform(0, 0.25), 3),
            "factors": {
                "usage_pattern": "regular",
                "season_adjustment": "normal",
                "inventory_status": "adequate"
            },
            "model_version": "mock-model-v1.0",
            "warnings": ["Using mock prediction service (development mode)"]
        }
    
    async def get_prediction_metrics(self) -> Dict[str, Any]:
        """
        Get prediction model performance metrics (mock)
        """
        return {
            "model_id": "mock-model-v1.0",
            "accuracy_metrics": {
                "mae": 2.5,  # Mean Absolute Error in days
                "rmse": 3.2,  # Root Mean Square Error
                "mape": 0.15  # Mean Absolute Percentage Error (15%)
            },
            "feature_importance": {
                "avg_daily_usage": 0.35,
                "days_since_last_order": 0.25,
                "customer_type": 0.15,
                "season": 0.10,
                "area": 0.08,
                "inventory": 0.07
            },
            "last_training_date": (datetime.now() - timedelta(days=7)).date().isoformat(),
            "model_status": "healthy",
            "total_predictions": 15420,
            "successful_predictions": 14890,
            "success_rate": 0.966,
            "warnings": ["Using mock metrics (development mode)"]
        }
    
    async def train_demand_model(self) -> Dict[str, Any]:
        """
        Mock model training (doesn't actually train)
        """
        # Simulate training time
        delay = random.uniform(2, 5)
        await asyncio.sleep(delay)
        
        logger.info("Mock model training completed")
        
        return {
            "model_id": f"mock-model-{datetime.now().strftime('%Y%m%d')}",
            "endpoint_id": f"mock-endpoint-{datetime.now().strftime('%Y%m%d')}",
            "model_name": f"demand_predictor_v{datetime.now().strftime('%Y%m%d')}",
            "status": "trained_and_deployed",
            "created_at": datetime.utcnow().isoformat(),
            "training_hours": round(delay / 3600, 2),
            "features_used": [
                "avg_daily_usage",
                "days_since_last_order", 
                "cylinder_inventory",
                "customer_type",
                "area",
                "temporal_features"
            ],
            "warnings": ["Mock training - no actual model created"]
        }