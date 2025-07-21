"""
Route optimization service integrating with Google Routes API
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import logging

from app.services.google_cloud.routes_service import google_routes_service
from app.models.route import Route as DeliveryRoute, RouteStop
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.models.vehicle import Vehicle
from app.core.database import get_async_session

logger = logging.getLogger(__name__)


class RouteOptimizationService:
    """
    Service for optimizing delivery routes
    """
    
    async def optimize_daily_routes(
        self,
        target_date: date,
        session: AsyncSession
    ) -> List[DeliveryRoute]:
        """
        Optimize all routes for a specific date
        """
        # Get pending orders for the date
        orders = await self._get_pending_orders(target_date, session)
        if not orders:
            logger.info(f"No pending orders for {target_date}")
            return []
        
        # Get available drivers
        drivers = await self._get_available_drivers(target_date, session)
        if not drivers:
            logger.warning(f"No available drivers for {target_date}")
            return []
        
        # Optimize routes using Google Routes API
        optimized_data = await google_routes_service.optimize_multiple_routes(
            orders=orders,
            drivers=drivers,
            date=target_date
        )
        
        # Create route records in database
        routes = []
        for route_data in optimized_data:
            route = await self._create_route_from_optimization(
                route_data, target_date, session
            )
            routes.append(route)
        
        await session.commit()
        return routes
    
    async def optimize_single_route(
        self,
        route_id: int,
        session: AsyncSession
    ) -> DeliveryRoute:
        """
        Re-optimize a single existing route
        """
        # Get route with stops
        route = await session.get(DeliveryRoute, route_id)
        if not route:
            raise ValueError(f"Route {route_id} not found")
        
        # Get orders for this route
        orders = await self._get_route_orders(route_id, session)
        
        # Prepare driver info
        driver_info = {
            "id": route.driver_id,
            "vehicle_id": route.vehicle_id,
            "vehicle_capacity": 100  # Default, should get from vehicle
        }
        
        # Optimize using Google Routes API
        optimized_data = await google_routes_service._optimize_driver_route(
            driver=driver_info,
            orders=orders,
            route_number=route.route_number
        )
        
        # Update route stops with optimized sequence
        await self._update_route_stops(route, optimized_data["stops"], session)
        
        # Update route metrics
        route.total_distance_km = optimized_data.get("total_distance_km", 0)
        route.estimated_duration_minutes = optimized_data.get("estimated_duration_minutes", 0)
        route.polyline = optimized_data.get("polyline", "")
        route.status = "optimized"
        
        await session.commit()
        return route
    
    async def _get_pending_orders(
        self,
        target_date: date,
        session: AsyncSession
    ) -> List[Order]:
        """Get pending orders for a specific date"""
        result = await session.execute(
            select(Order)
            .options(
                # Eager load customer relationship
                selectinload(Order.customer)
            )
            .where(
                and_(
                    Order.delivery_date == target_date,
                    Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED])
                )
            )
        )
        return list(result.scalars().all())
    
    async def _get_available_drivers(
        self,
        target_date: date,
        session: AsyncSession
    ) -> List[Dict]:
        """Get available drivers for a specific date"""
        # Get all drivers
        result = await session.execute(
            select(User)
            .where(
                and_(
                    User.role == "driver",
                    User.is_active == True
                )
            )
        )
        drivers = result.scalars().all()
        
        # Check which drivers already have routes for this date
        existing_routes = await session.execute(
            select(DeliveryRoute.driver_id)
            .where(DeliveryRoute.date == target_date)
        )
        busy_driver_ids = set(existing_routes.scalars().all())
        
        # Return available drivers
        available = []
        for driver in drivers:
            if driver.id not in busy_driver_ids:
                # Get driver's vehicle if assigned
                vehicle_id = None
                vehicle_capacity = 100  # Default
                
                # You might have a driver-vehicle assignment table
                # For now, using defaults
                
                available.append({
                    "id": driver.id,
                    "name": driver.username,
                    "vehicle_id": vehicle_id,
                    "vehicle_capacity": vehicle_capacity
                })
        
        return available
    
    async def _get_route_orders(
        self,
        route_id: int,
        session: AsyncSession
    ) -> List[Order]:
        """Get orders associated with a route"""
        result = await session.execute(
            select(Order)
            .join(RouteStop, RouteStop.order_id == Order.id)
            .options(selectinload(Order.customer))
            .where(RouteStop.route_id == route_id)
            .order_by(RouteStop.stop_sequence)
        )
        return list(result.scalars().all())
    
    async def _create_route_from_optimization(
        self,
        route_data: Dict,
        target_date: date,
        session: AsyncSession
    ) -> DeliveryRoute:
        """Create a route record from optimization data"""
        # Create route
        route = DeliveryRoute(
            route_number=route_data["route_number"],
            date=target_date,
            driver_id=route_data["driver_id"],
            vehicle_id=route_data.get("vehicle_id"),
            status=route_data.get("status", "optimized"),
            area=route_data.get("area", ""),
            total_stops=len(route_data["stops"]),
            completed_stops=0,
            total_distance_km=route_data.get("total_distance_km", 0),
            estimated_duration_minutes=route_data.get("estimated_duration_minutes", 0),
            polyline=route_data.get("polyline", "")
        )
        session.add(route)
        await session.flush()  # Get route ID
        
        # Create stops
        for stop_data in route_data["stops"]:
            stop = RouteStop(
                route_id=route.id,
                order_id=stop_data["order_id"],
                stop_sequence=stop_data["stop_sequence"],
                address=stop_data["address"],
                latitude=stop_data["lat"],
                longitude=stop_data["lng"],
                estimated_arrival=stop_data.get("estimated_arrival"),
                is_completed=False
            )
            session.add(stop)
            
            # Update order status
            order = await session.get(Order, stop_data["order_id"])
            if order:
                order.status = OrderStatus.ASSIGNED
                order.assigned_route_id = route.id
        
        return route
    
    async def _update_route_stops(
        self,
        route: DeliveryRoute,
        optimized_stops: List[Dict],
        session: AsyncSession
    ) -> None:
        """Update route stops with optimized sequence"""
        # Get existing stops
        result = await session.execute(
            select(RouteStop)
            .where(RouteStop.route_id == route.id)
        )
        existing_stops = {stop.order_id: stop for stop in result.scalars()}
        
        # Update sequence and arrival times
        for stop_data in optimized_stops:
            order_id = stop_data["order_id"]
            if order_id in existing_stops:
                stop = existing_stops[order_id]
                stop.stop_sequence = stop_data["stop_sequence"]
                stop.estimated_arrival = stop_data.get("estimated_arrival")
        
        # Update total stops
        route.total_stops = len(optimized_stops)


# Singleton instance
route_optimization_service = RouteOptimizationService()