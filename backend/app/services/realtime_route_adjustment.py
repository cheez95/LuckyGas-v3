"""
Real-time route adjustment service for handling dynamic route changes.
Handles urgent orders, traffic updates, and route rebalancing.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import route_adjustment_counter, route_adjustment_summary
from app.models.order import Order
from app.models.route import Route, RouteStop
from app.services.google_cloud.monitoring.intelligent_cache import \
    get_intelligent_cache
from app.services.google_cloud.routes_service import GoogleRoutesService
from app.services.optimization.vrp_optimizer import VRPOptimizer
from app.services.websocket_service import websocket_manager

logger = logging.getLogger(__name__)

# Will be initialized on first use
intelligent_cache = None


class AdjustmentType(Enum):
    """Types of route adjustments."""

    URGENT_ORDER = "urgent_order"
    TRAFFIC_UPDATE = "traffic_update"
    DRIVER_UNAVAILABLE = "driver_unavailable"
    CUSTOMER_CANCELLATION = "customer_cancellation"
    TIME_WINDOW_CHANGE = "time_window_change"
    VEHICLE_BREAKDOWN = "vehicle_breakdown"


@dataclass
class AdjustmentRequest:
    """Request for route adjustment."""

    route_id: str
    adjustment_type: AdjustmentType
    data: Dict
    priority: str = "normal"  # normal, high, urgent
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class AdjustmentResult:
    """Result of route adjustment."""

    success: bool
    original_route_id: str
    affected_routes: List[str]
    changes: List[Dict]
    new_total_distance: float
    new_total_time: float
    message: str
    optimization_time_ms: int


class RealtimeRouteAdjustmentService:
    """Service for real-time route adjustments."""

    def __init__(self):
        self.vrp_optimizer = VRPOptimizer()
        self.routes_service = GoogleRoutesService()
        self.adjustment_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False

    async def start_processing(self):
        """Start processing adjustment requests."""
        self._processing = True
        asyncio.create_task(self._process_adjustments())

    async def stop_processing(self):
        """Stop processing adjustment requests."""
        self._processing = False

    async def _process_adjustments(self):
        """Process adjustment requests from queue."""
        while self._processing:
            try:
                # Get adjustment request with timeout
                request = await asyncio.wait_for(
                    self.adjustment_queue.get(), timeout=1.0
                )

                # Process the adjustment
                await self._handle_adjustment(request)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing adjustment: {e}")

    async def _handle_adjustment(self, request: AdjustmentRequest):
        """Handle a single adjustment request."""
        start_time = datetime.utcnow()

        try:
            # Route to appropriate handler
            if request.adjustment_type == AdjustmentType.URGENT_ORDER:
                result = await self._handle_urgent_order(request)
            elif request.adjustment_type == AdjustmentType.TRAFFIC_UPDATE:
                result = await self._handle_traffic_update(request)
            elif request.adjustment_type == AdjustmentType.DRIVER_UNAVAILABLE:
                result = await self._handle_driver_unavailable(request)
            else:
                result = await self._handle_generic_adjustment(request)

            # Record metrics
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            route_adjustment_counter.labels(
                adjustment_type=request.adjustment_type.value,
                success=str(result.success).lower(),
            ).inc()
            route_adjustment_summary.observe(duration_ms)

            # Send WebSocket notification
            await self._notify_adjustment(result)

        except Exception as e:
            logger.error(f"Failed to handle adjustment {request}: {e}")

    async def add_urgent_order(
        self, order_id: str, route_id: Optional[str], session: AsyncSession
    ) -> AdjustmentResult:
        """Add an urgent order to existing routes."""
        request = AdjustmentRequest(
            route_id=route_id or "auto",
            adjustment_type=AdjustmentType.URGENT_ORDER,
            data={"order_id": order_id},
            priority="urgent",
        )

        return await self._handle_urgent_order(request, session)

    async def _handle_urgent_order(
        self, request: AdjustmentRequest, session: Optional[AsyncSession] = None
    ) -> AdjustmentResult:
        """Handle urgent order insertion."""
        start_time = datetime.utcnow()
        order_id = request.data.get("order_id")

        try:
            # Get order details
            order = await self._get_order(order_id, session)
            if not order:
                return AdjustmentResult(
                    success=False,
                    original_route_id=request.route_id,
                    affected_routes=[],
                    changes=[],
                    new_total_distance=0,
                    new_total_time=0,
                    message=f"Order {order_id} not found",
                    optimization_time_ms=0,
                )

            # Find best route for insertion
            if request.route_id == "auto":
                best_route = await self._find_best_route_for_order(order, session)
                if not best_route:
                    return AdjustmentResult(
                        success=False,
                        original_route_id="",
                        affected_routes=[],
                        changes=[],
                        new_total_distance=0,
                        new_total_time=0,
                        message="No suitable route found for urgent order",
                        optimization_time_ms=0,
                    )
                route_id = best_route.id
            else:
                route_id = request.route_id

            # Get current route
            route = await self._get_route(route_id, session)
            if not route:
                return AdjustmentResult(
                    success=False,
                    original_route_id=route_id,
                    affected_routes=[],
                    changes=[],
                    new_total_distance=0,
                    new_total_time=0,
                    message=f"Route {route_id} not found",
                    optimization_time_ms=0,
                )

            # Find optimal insertion point
            insertion_index = await self._find_optimal_insertion_point(
                route, order, session
            )

            # Insert the order
            new_stop = RouteStop(
                route_id=route.id,
                order_id=order.id,
                sequence=insertion_index,
                estimated_arrival=datetime.utcnow(),  # Will be recalculated
                estimated_duration=15,  # Default duration
                status="pending",
            )

            # Resequence stops
            for stop in route.stops:
                if stop.sequence >= insertion_index:
                    stop.sequence += 1

            route.stops.insert(insertion_index - 1, new_stop)

            # Recalculate route timing and distance
            await self._recalculate_route(route, session)

            # Save changes
            if session:
                session.add(route)
                await session.commit()

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            return AdjustmentResult(
                success=True,
                original_route_id=route_id,
                affected_routes=[route_id],
                changes=[
                    {
                        "type": "order_inserted",
                        "order_id": order_id,
                        "route_id": route_id,
                        "position": insertion_index,
                    }
                ],
                new_total_distance=route.total_distance_km,
                new_total_time=route.total_duration_minutes,
                message=f"Urgent order {order_id} added to route {route_id}",
                optimization_time_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Failed to handle urgent order: {e}")
            return AdjustmentResult(
                success=False,
                original_route_id=request.route_id,
                affected_routes=[],
                changes=[],
                new_total_distance=0,
                new_total_time=0,
                message=str(e),
                optimization_time_ms=0,
            )

    async def _handle_traffic_update(
        self, request: AdjustmentRequest
    ) -> AdjustmentResult:
        """Handle traffic-based route adjustments."""
        route_id = request.route_id
        traffic_data = request.data.get("traffic", {})

        try:
            # Get current route
            route = await self._get_route(route_id)
            if not route:
                return AdjustmentResult(
                    success=False,
                    original_route_id=route_id,
                    affected_routes=[],
                    changes=[],
                    new_total_distance=0,
                    new_total_time=0,
                    message=f"Route {route_id} not found",
                    optimization_time_ms=0,
                )

            # Get real-time traffic data from Google Routes API
            traffic_info = await self.routes_service.get_traffic_info(
                [stop.to_location() for stop in route.stops]
            )

            # Check if rerouting is beneficial
            current_time = sum(stop.estimated_duration for stop in route.stops)
            new_time = traffic_info.get("total_duration_minutes", current_time)

            if new_time > current_time * 1.2:  # 20% worse
                # Reoptimize the route
                optimized = await self.vrp_optimizer.optimize_single_route(
                    route, consider_traffic=True
                )

                if optimized and optimized.total_duration_minutes < new_time:
                    # Update route with optimized version
                    route.stops = optimized.stops
                    route.polyline = optimized.polyline
                    route.total_distance_km = optimized.total_distance_km
                    route.total_duration_minutes = optimized.total_duration_minutes

                    return AdjustmentResult(
                        success=True,
                        original_route_id=route_id,
                        affected_routes=[route_id],
                        changes=[
                            {
                                "type": "route_reoptimized",
                                "reason": "traffic",
                                "time_saved": new_time
                                - optimized.total_duration_minutes,
                            }
                        ],
                        new_total_distance=route.total_distance_km,
                        new_total_time=route.total_duration_minutes,
                        message=f"Route reoptimized due to traffic",
                        optimization_time_ms=100,
                    )

            return AdjustmentResult(
                success=True,
                original_route_id=route_id,
                affected_routes=[],
                changes=[],
                new_total_distance=route.total_distance_km,
                new_total_time=new_time,
                message="No reoptimization needed",
                optimization_time_ms=50,
            )

        except Exception as e:
            logger.error(f"Failed to handle traffic update: {e}")
            return AdjustmentResult(
                success=False,
                original_route_id=route_id,
                affected_routes=[],
                changes=[],
                new_total_distance=0,
                new_total_time=0,
                message=str(e),
                optimization_time_ms=0,
            )

    async def _find_best_route_for_order(
        self, order: Order, session: AsyncSession
    ) -> Optional[Route]:
        """Find the best route to insert an urgent order."""
        # Get active routes for today
        today = datetime.utcnow().date()
        stmt = select(Route).where(
            Route.route_date == today, Route.status.in_(["not_started", "in_progress"])
        )
        result = await session.execute(stmt)
        routes = result.scalars().all()

        if not routes:
            return None

        # Calculate insertion cost for each route
        best_route = None
        min_cost = float("inf")

        for route in routes:
            # Skip if vehicle capacity exceeded
            if not self._check_capacity(route, order):
                continue

            # Calculate detour cost
            cost = await self._calculate_insertion_cost(route, order)

            if cost < min_cost:
                min_cost = cost
                best_route = route

        return best_route

    async def _find_optimal_insertion_point(
        self, route: Route, order: Order, session: AsyncSession
    ) -> int:
        """Find the optimal position to insert an order in a route."""
        min_detour = float("inf")
        best_position = len(route.stops) + 1

        order_location = (order.delivery_latitude, order.delivery_longitude)

        for i in range(1, len(route.stops) + 2):
            # Calculate detour if inserting at position i
            if i == 1:
                # Insert at beginning
                if route.stops:
                    first_stop = route.stops[0]
                    detour = (
                        await self._calculate_distance(
                            route.depot_location, order_location
                        )
                        + await self._calculate_distance(
                            order_location, (first_stop.latitude, first_stop.longitude)
                        )
                        - await self._calculate_distance(
                            route.depot_location,
                            (first_stop.latitude, first_stop.longitude),
                        )
                    )
                else:
                    detour = 0
            elif i == len(route.stops) + 1:
                # Insert at end
                if route.stops:
                    last_stop = route.stops[-1]
                    detour = await self._calculate_distance(
                        (last_stop.latitude, last_stop.longitude), order_location
                    )
                else:
                    detour = await self._calculate_distance(
                        route.depot_location, order_location
                    )
            else:
                # Insert between stops
                prev_stop = route.stops[i - 2]
                next_stop = route.stops[i - 1]
                detour = (
                    await self._calculate_distance(
                        (prev_stop.latitude, prev_stop.longitude), order_location
                    )
                    + await self._calculate_distance(
                        order_location, (next_stop.latitude, next_stop.longitude)
                    )
                    - await self._calculate_distance(
                        (prev_stop.latitude, prev_stop.longitude),
                        (next_stop.latitude, next_stop.longitude),
                    )
                )

            if detour < min_detour:
                min_detour = detour
                best_position = i

        return best_position

    async def _recalculate_route(self, route: Route, session: AsyncSession):
        """Recalculate route timing and distance."""
        # Get distance matrix
        locations = [route.depot_location]
        for stop in route.stops:
            locations.append((stop.latitude, stop.longitude))

        # Get updated distances and times from Google Routes
        matrix = await self.routes_service.get_distance_matrix(locations)

        # Update route stats
        total_distance = 0
        total_time = 0
        current_time = route.start_time

        for i, stop in enumerate(route.stops):
            # Travel time from previous location
            travel_time = matrix[i][i + 1]["duration_minutes"]
            total_time += travel_time
            total_distance += matrix[i][i + 1]["distance_km"]

            # Update stop timing
            stop.estimated_arrival = current_time + timedelta(minutes=travel_time)
            current_time = stop.estimated_arrival + timedelta(
                minutes=stop.estimated_duration
            )

        route.total_distance_km = total_distance
        route.total_duration_minutes = total_time

    async def _notify_adjustment(self, result: AdjustmentResult):
        """Send WebSocket notification for route adjustment."""
        if result.success:
            for route_id in result.affected_routes:
                await websocket_manager.send_to_channel(
                    f"route:{route_id}",
                    {
                        "type": "route_adjustment",
                        "route_id": route_id,
                        "changes": result.changes,
                        "message": result.message,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

    # Helper methods
    async def _get_order(self, order_id: str, session: AsyncSession) -> Optional[Order]:
        """Get order by ID."""
        stmt = select(Order).where(Order.id == order_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_route(
        self, route_id: str, session: Optional[AsyncSession] = None
    ) -> Optional[Route]:
        """Get route by ID."""
        # Mock implementation for now
        return None

    def _check_capacity(self, route: Route, order: Order) -> bool:
        """Check if route has capacity for order."""
        # Calculate current load
        current_load = sum(
            stop.order.total_quantity for stop in route.stops if stop.order
        )

        # Check if adding order exceeds capacity
        return current_load + order.total_quantity <= route.vehicle.capacity

    async def _calculate_distance(
        self, from_loc: Tuple[float, float], to_loc: Tuple[float, float]
    ) -> float:
        """Calculate distance between two locations."""
        # Initialize cache if needed
        global intelligent_cache
        if intelligent_cache is None:
            intelligent_cache = await get_intelligent_cache()

        # Use cached distance if available
        cache_key = f"distance:{from_loc}:{to_loc}"
        cached = await intelligent_cache.get(cache_key)
        if cached:
            return cached

        # Calculate using haversine formula
        lat1, lon1 = from_loc
        lat2, lon2 = to_loc

        R = 6371  # Earth's radius in km
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = (
            np.sin(dlat / 2) ** 2
            + np.cos(np.radians(lat1))
            * np.cos(np.radians(lat2))
            * np.sin(dlon / 2) ** 2
        )
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        distance = R * c

        # Cache the result
        await intelligent_cache.set(cache_key, distance, ttl=3600)

        return distance

    async def _calculate_insertion_cost(self, route: Route, order: Order) -> float:
        """Calculate the cost of inserting an order into a route."""
        # Find best insertion point and calculate detour
        best_position = await self._find_optimal_insertion_point(route, order, None)

        # Simplified cost calculation
        order_location = (order.delivery_latitude, order.delivery_longitude)

        if best_position == 1 and route.stops:
            # Insert at beginning
            first_stop = route.stops[0]
            cost = await self._calculate_distance(
                route.depot_location, order_location
            ) + await self._calculate_distance(
                order_location, (first_stop.latitude, first_stop.longitude)
            )
        elif best_position == len(route.stops) + 1:
            # Insert at end
            if route.stops:
                last_stop = route.stops[-1]
                cost = await self._calculate_distance(
                    (last_stop.latitude, last_stop.longitude), order_location
                )
            else:
                cost = await self._calculate_distance(
                    route.depot_location, order_location
                )
        else:
            # Insert between stops
            prev_stop = route.stops[best_position - 2]
            next_stop = route.stops[best_position - 1]
            cost = await self._calculate_distance(
                (prev_stop.latitude, prev_stop.longitude), order_location
            ) + await self._calculate_distance(
                order_location, (next_stop.latitude, next_stop.longitude)
            )

        return cost

    async def _handle_driver_unavailable(
        self, request: AdjustmentRequest
    ) -> AdjustmentResult:
        """Handle driver unavailability by reassigning routes."""
        # Implementation for driver unavailability
        pass

    async def _handle_generic_adjustment(
        self, request: AdjustmentRequest
    ) -> AdjustmentResult:
        """Handle generic route adjustments."""
        # Implementation for other adjustment types
        pass


# Singleton instance
realtime_route_adjustment_service = RealtimeRouteAdjustmentService()
