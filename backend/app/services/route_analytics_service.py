"""
Route performance analytics service for tracking and analyzing delivery metrics.
"""
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.route import Route, RouteStop
from app.models.order import Order
from app.models.driver import Driver
from app.models.optimization import OptimizationHistory
from app.services.google_cloud.monitoring.intelligent_cache import get_intelligent_cache
from app.schemas.analytics import (
    RoutePerformanceMetrics,
    FuelSavingsReport,
    DriverPerformanceMetrics,
    DailyAnalyticsSummary,
    WeeklyTrendReport
)

logger = logging.getLogger(__name__)

# Will be initialized on first use
intelligent_cache = None


class MetricPeriod(Enum):
    """Time periods for analytics."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class RouteEfficiency:
    """Route efficiency metrics."""
    route_id: str
    planned_distance: float
    actual_distance: float
    planned_duration: float
    actual_duration: float
    fuel_consumed: float
    fuel_saved: float
    on_time_percentage: float
    customer_satisfaction: float
    cost_per_delivery: float


class RouteAnalyticsService:
    """Service for route performance analytics."""
    
    def __init__(self):
        self.fuel_price_per_liter = 30.0  # TWD per liter
        self.vehicle_fuel_efficiency = {
            "small": 8.0,   # km/liter for small trucks
            "medium": 6.0,  # km/liter for medium trucks
            "large": 4.0    # km/liter for large trucks
        }
        
    async def get_daily_analytics(
        self,
        target_date: date,
        session: AsyncSession
    ) -> DailyAnalyticsSummary:
        """Get comprehensive analytics for a specific day."""
        # Initialize cache if needed
        global intelligent_cache
        if intelligent_cache is None:
            intelligent_cache = await get_intelligent_cache()
        
        cache_key = f"analytics:daily:{target_date}"
        cached = await intelligent_cache.get(cache_key)
        if cached:
            return DailyAnalyticsSummary(**cached)
            
        # Get all routes for the day
        stmt = select(Route).options(
            selectinload(Route.stops),
            selectinload(Route.driver)
        ).where(Route.route_date == target_date)
        
        result = await session.execute(stmt)
        routes = result.scalars().all()
        
        if not routes:
            return DailyAnalyticsSummary(
                date=target_date,
                total_routes=0,
                total_deliveries=0,
                total_distance_km=0,
                total_fuel_saved_liters=0,
                total_cost_saved=0,
                average_delay_minutes=0,
                on_time_percentage=0,
                optimization_savings_percentage=0
            )
            
        # Calculate metrics
        total_routes = len(routes)
        total_deliveries = sum(len(r.stops) for r in routes)
        total_distance = sum(r.total_distance_km for r in routes)
        
        # Calculate fuel savings
        fuel_metrics = await self._calculate_fuel_savings(routes, session)
        
        # Calculate time metrics
        time_metrics = self._calculate_time_metrics(routes)
        
        # Get optimization savings
        optimization_metrics = await self._get_optimization_metrics(target_date, session)
        
        summary = DailyAnalyticsSummary(
            date=target_date,
            total_routes=total_routes,
            total_deliveries=total_deliveries,
            total_distance_km=total_distance,
            total_fuel_saved_liters=fuel_metrics['total_saved'],
            total_cost_saved=fuel_metrics['cost_saved'],
            average_delay_minutes=time_metrics['avg_delay'],
            on_time_percentage=time_metrics['on_time_pct'],
            optimization_savings_percentage=optimization_metrics['savings_pct'],
            routes_by_status=self._count_routes_by_status(routes),
            deliveries_by_hour=self._get_deliveries_by_hour(routes),
            top_performing_drivers=await self._get_top_drivers(routes, session)
        )
        
        # Cache for 1 hour
        await intelligent_cache.set(cache_key, asdict(summary), ttl=3600)
        
        return summary
        
    async def get_weekly_trends(
        self,
        end_date: date,
        session: AsyncSession
    ) -> WeeklyTrendReport:
        """Get weekly trend analysis."""
        start_date = end_date - timedelta(days=6)
        
        # Get daily summaries for the week
        daily_summaries = []
        for i in range(7):
            day = start_date + timedelta(days=i)
            summary = await self.get_daily_analytics(day, session)
            daily_summaries.append(summary)
            
        # Calculate trends
        distances = [s.total_distance_km for s in daily_summaries]
        fuel_saved = [s.total_fuel_saved_liters for s in daily_summaries]
        on_time_pcts = [s.on_time_percentage for s in daily_summaries if s.total_routes > 0]
        
        return WeeklyTrendReport(
            start_date=start_date,
            end_date=end_date,
            daily_summaries=daily_summaries,
            distance_trend=self._calculate_trend(distances),
            fuel_savings_trend=self._calculate_trend(fuel_saved),
            on_time_trend=self._calculate_trend(on_time_pcts),
            total_distance_km=sum(distances),
            total_fuel_saved_liters=sum(fuel_saved),
            total_cost_saved=sum(s.total_cost_saved for s in daily_summaries),
            average_daily_routes=sum(s.total_routes for s in daily_summaries) / 7,
            busiest_day=self._find_busiest_day(daily_summaries),
            improvement_suggestions=self._generate_suggestions(daily_summaries)
        )
        
    async def get_driver_performance(
        self,
        driver_id: str,
        period: MetricPeriod,
        end_date: date,
        session: AsyncSession
    ) -> DriverPerformanceMetrics:
        """Get performance metrics for a specific driver."""
        # Determine date range
        if period == MetricPeriod.DAILY:
            start_date = end_date
        elif period == MetricPeriod.WEEKLY:
            start_date = end_date - timedelta(days=6)
        elif period == MetricPeriod.MONTHLY:
            start_date = end_date - timedelta(days=29)
        else:
            start_date = end_date - timedelta(days=89)
            
        # Get driver's routes
        stmt = select(Route).options(
            selectinload(Route.stops)
        ).where(
            and_(
                Route.driver_id == driver_id,
                Route.route_date >= start_date,
                Route.route_date <= end_date
            )
        )
        
        result = await session.execute(stmt)
        routes = result.scalars().all()
        
        if not routes:
            return DriverPerformanceMetrics(
                driver_id=driver_id,
                period=period.value,
                start_date=start_date,
                end_date=end_date,
                total_routes=0,
                total_deliveries=0,
                total_distance_km=0,
                average_deliveries_per_route=0,
                on_time_percentage=0,
                average_delay_minutes=0,
                fuel_efficiency_score=0,
                customer_satisfaction_score=0,
                overall_score=0
            )
            
        # Calculate metrics
        total_routes = len(routes)
        total_deliveries = sum(len(r.stops) for r in routes)
        total_distance = sum(r.total_distance_km for r in routes)
        
        # Time metrics
        on_time_deliveries = sum(
            1 for r in routes 
            for s in r.stops 
            if s.status == 'completed' and s.actual_arrival <= s.estimated_arrival
        )
        total_completed = sum(
            1 for r in routes 
            for s in r.stops 
            if s.status == 'completed'
        )
        
        on_time_pct = (on_time_deliveries / total_completed * 100) if total_completed > 0 else 0
        
        # Calculate average delay
        delays = []
        for route in routes:
            for stop in route.stops:
                if stop.status == 'completed' and stop.actual_arrival:
                    delay = (stop.actual_arrival - stop.estimated_arrival).total_seconds() / 60
                    if delay > 0:
                        delays.append(delay)
                        
        avg_delay = np.mean(delays) if delays else 0
        
        # Fuel efficiency score (compared to average)
        fuel_score = await self._calculate_fuel_efficiency_score(routes, session)
        
        # Customer satisfaction (mock for now)
        satisfaction_score = 85 + np.random.randint(-5, 10)
        
        # Overall score
        overall_score = (
            on_time_pct * 0.3 +
            fuel_score * 0.2 +
            satisfaction_score * 0.3 +
            (100 - min(avg_delay, 30) / 30 * 100) * 0.2
        )
        
        return DriverPerformanceMetrics(
            driver_id=driver_id,
            period=period.value,
            start_date=start_date,
            end_date=end_date,
            total_routes=total_routes,
            total_deliveries=total_deliveries,
            total_distance_km=total_distance,
            average_deliveries_per_route=total_deliveries / total_routes,
            on_time_percentage=on_time_pct,
            average_delay_minutes=avg_delay,
            fuel_efficiency_score=fuel_score,
            customer_satisfaction_score=satisfaction_score,
            overall_score=overall_score,
            daily_breakdown=await self._get_driver_daily_breakdown(driver_id, start_date, end_date, session)
        )
        
    async def get_fuel_savings_report(
        self,
        start_date: date,
        end_date: date,
        session: AsyncSession
    ) -> FuelSavingsReport:
        """Generate comprehensive fuel savings report."""
        # Get optimization history
        stmt = select(OptimizationHistory).where(
            and_(
                OptimizationHistory.created_at >= start_date,
                OptimizationHistory.created_at <= end_date,
                OptimizationHistory.success == True
            )
        )
        
        result = await session.execute(stmt)
        optimizations = result.scalars().all()
        
        # Calculate savings
        total_baseline_distance = 0
        total_optimized_distance = 0
        
        for opt in optimizations:
            if opt.response_data:
                baseline = opt.response_data.get('baseline_distance_km', 0)
                optimized = opt.total_distance_km or 0
                total_baseline_distance += baseline
                total_optimized_distance += optimized
                
        distance_saved = total_baseline_distance - total_optimized_distance
        
        # Calculate fuel metrics
        avg_efficiency = np.mean(list(self.vehicle_fuel_efficiency.values()))
        baseline_fuel = total_baseline_distance / avg_efficiency
        optimized_fuel = total_optimized_distance / avg_efficiency
        fuel_saved = baseline_fuel - optimized_fuel
        cost_saved = fuel_saved * self.fuel_price_per_liter
        
        # CO2 emissions (2.31 kg CO2 per liter of diesel)
        co2_saved = fuel_saved * 2.31
        
        return FuelSavingsReport(
            start_date=start_date,
            end_date=end_date,
            total_distance_baseline_km=total_baseline_distance,
            total_distance_optimized_km=total_optimized_distance,
            total_distance_saved_km=distance_saved,
            total_fuel_baseline_liters=baseline_fuel,
            total_fuel_optimized_liters=optimized_fuel,
            total_fuel_saved_liters=fuel_saved,
            total_cost_saved_twd=cost_saved,
            co2_emissions_saved_kg=co2_saved,
            savings_percentage=(distance_saved / total_baseline_distance * 100) if total_baseline_distance > 0 else 0,
            daily_breakdown=await self._get_daily_fuel_breakdown(start_date, end_date, session),
            vehicle_type_breakdown=await self._get_vehicle_fuel_breakdown(start_date, end_date, session)
        )
        
    async def _calculate_fuel_savings(
        self,
        routes: List[Route],
        session: AsyncSession
    ) -> Dict[str, float]:
        """Calculate fuel savings for routes."""
        total_distance = sum(r.total_distance_km for r in routes)
        
        # Get baseline distance (before optimization)
        baseline_distance = total_distance * 1.25  # Assume 25% improvement
        
        # Calculate fuel consumption
        avg_efficiency = np.mean(list(self.vehicle_fuel_efficiency.values()))
        baseline_fuel = baseline_distance / avg_efficiency
        actual_fuel = total_distance / avg_efficiency
        
        fuel_saved = baseline_fuel - actual_fuel
        cost_saved = fuel_saved * self.fuel_price_per_liter
        
        return {
            'total_saved': fuel_saved,
            'cost_saved': cost_saved,
            'baseline_fuel': baseline_fuel,
            'actual_fuel': actual_fuel
        }
        
    def _calculate_time_metrics(self, routes: List[Route]) -> Dict[str, float]:
        """Calculate time-based metrics."""
        total_stops = 0
        on_time_stops = 0
        delays = []
        
        for route in routes:
            for stop in route.stops:
                if stop.status == 'completed':
                    total_stops += 1
                    if stop.actual_arrival and stop.estimated_arrival:
                        delay = (stop.actual_arrival - stop.estimated_arrival).total_seconds() / 60
                        if delay <= 0:
                            on_time_stops += 1
                        else:
                            delays.append(delay)
                            
        on_time_pct = (on_time_stops / total_stops * 100) if total_stops > 0 else 0
        avg_delay = np.mean(delays) if delays else 0
        
        return {
            'on_time_pct': on_time_pct,
            'avg_delay': avg_delay,
            'total_stops': total_stops,
            'on_time_stops': on_time_stops
        }
        
    async def _get_optimization_metrics(
        self,
        target_date: date,
        session: AsyncSession
    ) -> Dict[str, float]:
        """Get optimization metrics for a date."""
        stmt = select(OptimizationHistory).where(
            func.date(OptimizationHistory.created_at) == target_date
        )
        
        result = await session.execute(stmt)
        optimizations = result.scalars().all()
        
        if not optimizations:
            return {'savings_pct': 0, 'total_optimizations': 0}
            
        savings_percentages = [
            opt.savings_percentage 
            for opt in optimizations 
            if opt.savings_percentage
        ]
        
        return {
            'savings_pct': np.mean(savings_percentages) if savings_percentages else 0,
            'total_optimizations': len(optimizations)
        }
        
    def _count_routes_by_status(self, routes: List[Route]) -> Dict[str, int]:
        """Count routes by status."""
        status_counts = {
            'completed': 0,
            'in_progress': 0,
            'not_started': 0,
            'delayed': 0
        }
        
        for route in routes:
            if route.status in status_counts:
                status_counts[route.status] += 1
                
        return status_counts
        
    def _get_deliveries_by_hour(self, routes: List[Route]) -> Dict[int, int]:
        """Get delivery count by hour."""
        hourly_counts = {h: 0 for h in range(24)}
        
        for route in routes:
            for stop in route.stops:
                if stop.status == 'completed' and stop.actual_arrival:
                    hour = stop.actual_arrival.hour
                    hourly_counts[hour] += 1
                    
        return hourly_counts
        
    async def _get_top_drivers(
        self,
        routes: List[Route],
        session: AsyncSession
    ) -> List[Dict[str, any]]:
        """Get top performing drivers."""
        driver_stats = {}
        
        for route in routes:
            if route.driver_id not in driver_stats:
                driver_stats[route.driver_id] = {
                    'driver_id': route.driver_id,
                    'driver_name': route.driver.name if route.driver else 'Unknown',
                    'routes': 0,
                    'deliveries': 0,
                    'on_time': 0,
                    'total': 0
                }
                
            stats = driver_stats[route.driver_id]
            stats['routes'] += 1
            
            for stop in route.stops:
                if stop.status == 'completed':
                    stats['deliveries'] += 1
                    stats['total'] += 1
                    if stop.actual_arrival and stop.actual_arrival <= stop.estimated_arrival:
                        stats['on_time'] += 1
                        
        # Calculate on-time percentage
        for stats in driver_stats.values():
            stats['on_time_pct'] = (stats['on_time'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
        # Sort by on-time percentage
        top_drivers = sorted(
            driver_stats.values(),
            key=lambda x: x['on_time_pct'],
            reverse=True
        )[:5]
        
        return top_drivers
        
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction."""
        if len(values) < 2:
            return "stable"
            
        # Simple linear regression
        x = np.arange(len(values))
        if np.sum(values) == 0:
            return "stable"
            
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
            
    def _find_busiest_day(self, summaries: List[DailyAnalyticsSummary]) -> str:
        """Find the busiest day of the week."""
        max_deliveries = 0
        busiest_day = ""
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for i, summary in enumerate(summaries):
            if summary.total_deliveries > max_deliveries:
                max_deliveries = summary.total_deliveries
                busiest_day = days[i]
                
        return busiest_day
        
    def _generate_suggestions(self, summaries: List[DailyAnalyticsSummary]) -> List[str]:
        """Generate improvement suggestions based on data."""
        suggestions = []
        
        # Check on-time performance
        avg_on_time = np.mean([s.on_time_percentage for s in summaries if s.total_routes > 0])
        if avg_on_time < 80:
            suggestions.append("Consider adjusting time windows or adding buffer time to routes")
            
        # Check fuel savings
        total_fuel_saved = sum(s.total_fuel_saved_liters for s in summaries)
        if total_fuel_saved < 100:
            suggestions.append("Increase route optimization frequency to improve fuel savings")
            
        # Check for day patterns
        daily_deliveries = [s.total_deliveries for s in summaries]
        if max(daily_deliveries) > 2 * min(daily_deliveries):
            suggestions.append("Consider load balancing across weekdays to improve efficiency")
            
        return suggestions
        
    async def _calculate_fuel_efficiency_score(
        self,
        routes: List[Route],
        session: AsyncSession
    ) -> float:
        """Calculate fuel efficiency score for routes."""
        if not routes:
            return 0
            
        # Get average fuel consumption
        total_distance = sum(r.total_distance_km for r in routes)
        vehicle_type = "medium"  # Default, should get from route
        
        expected_fuel = total_distance / self.vehicle_fuel_efficiency[vehicle_type]
        
        # Compare to fleet average (mock)
        fleet_avg_efficiency = self.vehicle_fuel_efficiency[vehicle_type] * 0.9
        actual_fuel = total_distance / fleet_avg_efficiency
        
        # Score based on efficiency
        efficiency_ratio = expected_fuel / actual_fuel
        score = min(100, efficiency_ratio * 100)
        
        return score
        
    async def _get_driver_daily_breakdown(
        self,
        driver_id: str,
        start_date: date,
        end_date: date,
        session: AsyncSession
    ) -> List[Dict]:
        """Get daily breakdown for driver."""
        breakdown = []
        current = start_date
        
        while current <= end_date:
            stmt = select(Route).options(
                selectinload(Route.stops)
            ).where(
                and_(
                    Route.driver_id == driver_id,
                    Route.route_date == current
                )
            )
            
            result = await session.execute(stmt)
            routes = result.scalars().all()
            
            daily_stats = {
                'date': current,
                'routes': len(routes),
                'deliveries': sum(len(r.stops) for r in routes),
                'distance_km': sum(r.total_distance_km for r in routes),
                'on_time_pct': 0
            }
            
            # Calculate on-time percentage
            total = sum(1 for r in routes for s in r.stops if s.status == 'completed')
            on_time = sum(
                1 for r in routes for s in r.stops 
                if s.status == 'completed' and s.actual_arrival and s.actual_arrival <= s.estimated_arrival
            )
            
            if total > 0:
                daily_stats['on_time_pct'] = on_time / total * 100
                
            breakdown.append(daily_stats)
            current += timedelta(days=1)
            
        return breakdown
        
    async def _get_daily_fuel_breakdown(
        self,
        start_date: date,
        end_date: date,
        session: AsyncSession
    ) -> List[Dict]:
        """Get daily fuel breakdown."""
        breakdown = []
        current = start_date
        
        while current <= end_date:
            summary = await self.get_daily_analytics(current, session)
            breakdown.append({
                'date': current,
                'fuel_saved': summary.total_fuel_saved_liters,
                'cost_saved': summary.total_cost_saved,
                'distance_saved': summary.total_distance_km * 0.2  # Estimate
            })
            current += timedelta(days=1)
            
        return breakdown
        
    async def _get_vehicle_fuel_breakdown(
        self,
        start_date: date,
        end_date: date,
        session: AsyncSession
    ) -> Dict[str, Dict]:
        """Get fuel breakdown by vehicle type."""
        # Mock implementation
        return {
            'small': {
                'total_distance': 1200,
                'fuel_saved': 50,
                'cost_saved': 1500
            },
            'medium': {
                'total_distance': 2400,
                'fuel_saved': 120,
                'cost_saved': 3600
            },
            'large': {
                'total_distance': 800,
                'fuel_saved': 60,
                'cost_saved': 1800
            }
        }


# Singleton instance
route_analytics_service = RouteAnalyticsService()