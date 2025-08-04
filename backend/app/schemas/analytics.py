"""
Analytics schemas for route performance metrics.
"""

from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Dict, Optional
from enum import Enum


class MetricPeriod(str, Enum):
    """Time periods for analytics."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class RoutePerformanceMetrics(BaseModel):
    """Route performance metrics."""

    route_id: str
    date: date
    total_distance_km: float
    total_duration_minutes: float
    stops_completed: int
    on_time_percentage: float
    fuel_consumed_liters: float
    customer_satisfaction_score: float


class FuelSavingsReport(BaseModel):
    """Fuel savings report."""

    start_date: date
    end_date: date
    total_distance_baseline_km: float
    total_distance_optimized_km: float
    total_distance_saved_km: float
    total_fuel_baseline_liters: float
    total_fuel_optimized_liters: float
    total_fuel_saved_liters: float
    total_cost_saved_twd: float
    co2_emissions_saved_kg: float
    savings_percentage: float
    daily_breakdown: List[Dict]
    vehicle_type_breakdown: Dict[str, Dict]


class DriverPerformanceMetrics(BaseModel):
    """Driver performance metrics."""

    driver_id: str
    driver_name: Optional[str]
    period: str
    start_date: date
    end_date: date
    total_routes: int
    total_deliveries: int
    total_distance_km: float
    average_deliveries_per_route: float
    on_time_percentage: float
    average_delay_minutes: float
    fuel_efficiency_score: float
    customer_satisfaction_score: float
    overall_score: float
    daily_breakdown: Optional[List[Dict]] = []


class DailyAnalyticsSummary(BaseModel):
    """Daily analytics summary."""

    date: date
    total_routes: int
    total_deliveries: int
    total_distance_km: float
    total_fuel_saved_liters: float
    total_cost_saved: float
    average_delay_minutes: float
    on_time_percentage: float
    optimization_savings_percentage: float
    routes_by_status: Optional[Dict[str, int]] = {}
    deliveries_by_hour: Optional[Dict[int, int]] = {}
    top_performing_drivers: Optional[List[Dict]] = []


class WeeklyTrendReport(BaseModel):
    """Weekly trend analysis report."""

    start_date: date
    end_date: date
    daily_summaries: List[DailyAnalyticsSummary]
    distance_trend: str  # increasing, decreasing, stable
    fuel_savings_trend: str
    on_time_trend: str
    total_distance_km: float
    total_fuel_saved_liters: float
    total_cost_saved: float
    average_daily_routes: float
    busiest_day: str
    improvement_suggestions: List[str]
