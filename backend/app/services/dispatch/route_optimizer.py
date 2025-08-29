"""
Route optimization service for intelligent delivery planning
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.services.dispatch.google_routes_service import (
    Location,
    RouteRequest,
    RouteStop,
    get_routes_service,
)

logger = logging.getLogger(__name__)


@dataclass
class VehicleCapacity:
    """Vehicle capacity constraints"""

    max_weight_kg: float = 1000.0  # Default 1 ton
    max_cylinders_50kg: int = 20
    max_cylinders_20kg: int = 50
    max_cylinders_16kg: int = 60
    max_cylinders_10kg: int = 100
    max_cylinders_4kg: int = 200


@dataclass
class DriverConstraints:
    """Driver working constraints"""

    start_location: Location
    end_location: Optional[Location] = None  # If None, return to start
    start_time: time = time(8, 0)  # 8:00 AM
    end_time: time = time(18, 0)  # 6:00 PM
    break_duration_minutes: int = 60  # 1 hour lunch break
    break_start_time: time = time(12, 0)  # 12:00 PM
    max_driving_hours: float = 8.0
    vehicle_capacity: VehicleCapacity = None


@dataclass
class OptimizationRequest:
    """Request for route optimization"""

    date: datetime
    area: Optional[str] = None  # Filter by area
    drivers: List[Tuple[User, DriverConstraints]]  # List of (driver, constraints)
    priority_order_ids: List[int] = None  # Orders that must be delivered
    optimization_mode: str = "balanced"  # balanced, distance, time
    allow_split_orders: bool = True  # Allow splitting large orders


@dataclass
class OptimizedRoute:
    """Result of route optimization for a single driver"""

    driver_id: int
    route_date: datetime
    stops: List[Dict[str, Any]]  # Ordered list of stops
    total_distance_km: float
    total_duration_minutes: float
    total_weight_kg: float
    cylinder_counts: Dict[str, int]
    estimated_start_time: datetime
    estimated_end_time: datetime
    optimization_score: float
    warnings: List[str]


class RouteOptimizer:
    """Service for optimizing delivery routes"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.routes_service = None

    async def initialize(self):
        """Initialize the optimizer"""
        if not self.routes_service:
            self.routes_service = await get_routes_service()

    async def optimize_daily_routes(
        self, request: OptimizationRequest
    ) -> List[OptimizedRoute]:
        """
        Optimize routes for all drivers for a given day

        Args:
            request: Optimization request with date and constraints

        Returns:
            List of optimized routes, one per driver
        """
        await self.initialize()

        # 1. Fetch all pending orders for the date
        orders = await self._fetch_pending_orders(request.date, request.area)

        if not orders:
            logger.info(f"No pending orders for {request.date}")
            return []

        logger.info(
            f"Optimizing routes for {len(orders)} orders and {len(request.drivers)} drivers"
        )

        # 2. Cluster orders by geographic proximity
        clusters = await self._cluster_orders_by_location(orders)

        # 3. Assign clusters to drivers based on capacity and location
        driver_assignments = await self._assign_clusters_to_drivers(
            clusters, request.drivers, request.priority_order_ids
        )

        # 4. Optimize route for each driver
        optimized_routes = []
        for driver, constraints, assigned_orders in driver_assignments:
            if not assigned_orders:
                continue

            route = await self._optimize_driver_route(
                driver, constraints, assigned_orders, request.date
            )

            if route:
                optimized_routes.append(route)

        # 5. Balance workload if needed
        if request.optimization_mode == "balanced":
            optimized_routes = await self._balance_driver_workload(optimized_routes)

        return optimized_routes

    async def optimize_single_route(
        self,
        driver: User,
        orders: List[Order],
        constraints: DriverConstraints,
        route_date: datetime,
    ) -> OptimizedRoute:
        """
        Optimize route for a single driver

        Args:
            driver: Driver user
            orders: List of orders to deliver
            constraints: Driver constraints
            route_date: Date of the route

        Returns:
            Optimized route for the driver
        """
        await self.initialize()

        return await self._optimize_driver_route(
            driver, constraints, orders, route_date
        )

    async def _fetch_pending_orders(
        self, date: datetime, area: Optional[str] = None
    ) -> List[Order]:
        """Fetch all pending orders for the given date"""
        query = (
            select(Order)
            .where(
                and_(
                    Order.scheduled_date == date.date(),
                    Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED]),
                )
            )
            .options(selectinload(Order.customer), selectinload(Order.products))
        )

        if area:
            query = query.join(Customer).where(Customer.area == area)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _cluster_orders_by_location(
        self, orders: List[Order]
    ) -> List[List[Order]]:
        """
        Cluster orders by geographic proximity using simple grid - based clustering
        """
        # Group orders by area first
        area_groups = defaultdict(list)
        for order in orders:
            area = order.customer.area or "未分區"
            area_groups[area].append(order)

        # For each area, further cluster by proximity
        all_clusters = []
        for area, area_orders in area_groups.items():
            # Simple grid - based clustering
            # In production, use more sophisticated clustering like DBSCAN
            clusters = self._grid_cluster_orders(area_orders, grid_size_km=2.0)
            all_clusters.extend(clusters)

        return all_clusters

    def _grid_cluster_orders(
        self, orders: List[Order], grid_size_km: float = 2.0
    ) -> List[List[Order]]:
        """Simple grid - based clustering of orders"""
        if not orders:
            return []

        # Convert grid size to approximate degrees (1 degree ≈ 111 km)
        grid_size_deg = grid_size_km / 111.0

        # Group orders by grid cell
        grid_cells = defaultdict(list)
        for order in orders:
            # Get customer coordinates (would need geocoding in production)
            # For now, use a simple hash of the address
            lat = hash(order.customer.address) % 1000 / 1000.0 + 25.0  # Around Taipei
            lng = hash(order.customer.address + "lng") % 1000 / 1000.0 + 121.5

            # Calculate grid cell
            grid_x = int(lat / grid_size_deg)
            grid_y = int(lng / grid_size_deg)

            grid_cells[(grid_x, grid_y)].append(order)

        return list(grid_cells.values())

    async def _assign_clusters_to_drivers(
        self,
        clusters: List[List[Order]],
        drivers: List[Tuple[User, DriverConstraints]],
        priority_order_ids: Optional[List[int]] = None,
    ) -> List[Tuple[User, DriverConstraints, List[Order]]]:
        """Assign order clusters to drivers based on capacity and location"""
        assignments = []
        remaining_clusters = clusters.copy()

        # First, handle priority orders
        if priority_order_ids:
            for driver, constraints in drivers:
                driver_orders = []
                remaining_capacity = constraints.vehicle_capacity or VehicleCapacity()

                # Assign priority orders first
                for cluster in remaining_clusters[:]:
                    cluster_has_priority = any(
                        order.id in priority_order_ids for order in cluster
                    )

                    if cluster_has_priority and self._can_fit_orders(
                        cluster, remaining_capacity
                    ):
                        driver_orders.extend(cluster)
                        remaining_clusters.remove(cluster)
                        remaining_capacity = self._update_remaining_capacity(
                            remaining_capacity, cluster
                        )

                if driver_orders:
                    assignments.append((driver, constraints, driver_orders))

        # Then assign remaining clusters
        for driver, constraints in drivers:
            if any(d[0].id == driver.id for d in assignments):
                # Driver already has priority orders
                existing = next(a for a in assignments if a[0].id == driver.id)
                driver_orders = existing[2]
                remaining_capacity = self._calculate_remaining_capacity(
                    constraints.vehicle_capacity or VehicleCapacity(), driver_orders
                )
            else:
                driver_orders = []
                remaining_capacity = constraints.vehicle_capacity or VehicleCapacity()

            # Assign clusters that fit in remaining capacity
            for cluster in remaining_clusters[:]:
                if self._can_fit_orders(cluster, remaining_capacity):
                    driver_orders.extend(cluster)
                    remaining_clusters.remove(cluster)
                    remaining_capacity = self._update_remaining_capacity(
                        remaining_capacity, cluster
                    )

            if driver_orders and not any(d[0].id == driver.id for d in assignments):
                assignments.append((driver, constraints, driver_orders))

        # Log any unassigned orders
        if remaining_clusters:
            unassigned_count = sum(len(cluster) for cluster in remaining_clusters)
            logger.warning(
                f"{unassigned_count} orders could not be assigned to any driver"
            )

        return assignments

    async def _optimize_driver_route(
        self,
        driver: User,
        constraints: DriverConstraints,
        orders: List[Order],
        route_date: datetime,
    ) -> OptimizedRoute:
        """Optimize route for a single driver"""
        if not orders:
            return None

        # Convert orders to route stops
        stops = []
        for order in orders:
            # In production, use actual geocoding
            lat = hash(order.customer.address) % 1000 / 1000.0 + 25.0
            lng = hash(order.customer.address + "lng") % 1000 / 1000.0 + 121.5

            location = Location(
                latitude=lat,
                longitude=lng,
                address=order.delivery_address or order.customer.address,
            )

            stop = RouteStop(
                location=location,
                order_id=str(order.id),
                priority=5 if order.is_urgent else 1,
                service_duration_minutes=self._estimate_service_duration(order),
            )
            stops.append(stop)

        # Create route request
        route_request = RouteRequest(
            origin=constraints.start_location,
            destination=constraints.end_location or constraints.start_location,
            waypoints=stops,
            departure_time=datetime.combine(route_date.date(), constraints.start_time),
            optimize_waypoint_order=True,
        )

        try:
            # Call Google Routes API
            result = await self.routes_service.optimize_route(route_request)

            # Build optimized route
            optimized_stops = []
            for idx in result.optimized_waypoint_order:
                stop = stops[idx]
                order = next(o for o in orders if str(o.id) == stop.order_id)

                optimized_stops.append(
                    {
                        "sequence": len(optimized_stops) + 1,
                        "order_id": order.id,
                        "customer_name": order.customer.short_name,
                        "address": order.delivery_address or order.customer.address,
                        "products": self._format_order_products(order),
                        "estimated_arrival": None,  # Calculate based on route
                        "service_duration": stop.service_duration_minutes,
                        "priority": stop.priority,
                        "notes": order.delivery_notes,
                    }
                )

            # Calculate totals
            total_weight, cylinder_counts = self._calculate_order_totals(orders)

            # Estimate timing
            start_time = datetime.combine(route_date.date(), constraints.start_time)
            end_time = start_time + timedelta(
                seconds=int(result.total_duration_seconds)
            )

            return OptimizedRoute(
                driver_id=driver.id,
                route_date=route_date,
                stops=optimized_stops,
                total_distance_km=result.total_distance_meters / 1000.0,
                total_duration_minutes=int(result.total_duration_seconds) / 60.0,
                total_weight_kg=total_weight,
                cylinder_counts=cylinder_counts,
                estimated_start_time=start_time,
                estimated_end_time=end_time,
                optimization_score=self._calculate_optimization_score(
                    result, orders, constraints
                ),
                warnings=result.warnings,
            )

        except Exception as e:
            logger.error(f"Error optimizing route for driver {driver.id}: {e}")
            # Return unoptimized route
            return self._create_fallback_route(driver, orders, constraints, route_date)

    def _can_fit_orders(self, orders: List[Order], capacity: VehicleCapacity) -> bool:
        """Check if orders fit within vehicle capacity"""
        total_weight = 0
        cylinders = defaultdict(int)

        for order in orders:
            weight, counts = self._calculate_order_weight_and_cylinders(order)
            total_weight += weight
            for size, count in counts.items():
                cylinders[size] += count

        # Check weight limit
        if total_weight > capacity.max_weight_kg:
            return False

        # Check cylinder limits
        if (
            cylinders.get("50kg", 0) > capacity.max_cylinders_50kg
            or cylinders.get("20kg", 0) > capacity.max_cylinders_20kg
            or cylinders.get("16kg", 0) > capacity.max_cylinders_16kg
            or cylinders.get("10kg", 0) > capacity.max_cylinders_10kg
            or cylinders.get("4kg", 0) > capacity.max_cylinders_4kg
        ):
            return False

        return True

    def _calculate_order_weight_and_cylinders(
        self, order: Order
    ) -> Tuple[float, Dict[str, int]]:
        """Calculate total weight and cylinder counts for an order"""
        total_weight = 0
        cylinders = {
            "50kg": order.qty_50kg or 0,
            "20kg": order.qty_20kg or 0,
            "16kg": order.qty_16kg or 0,
            "10kg": order.qty_10kg or 0,
            "4kg": order.qty_4kg or 0,
        }

        # Calculate total weight (cylinder + gas weight)
        weights = {
            "50kg": 75,  # 50kg gas + 25kg cylinder
            "20kg": 30,  # 20kg gas + 10kg cylinder
            "16kg": 24,  # 16kg gas + 8kg cylinder
            "10kg": 15,  # 10kg gas + 5kg cylinder
            "4kg": 6,  # 4kg gas + 2kg cylinder
        }

        for size, count in cylinders.items():
            total_weight += weights.get(size, 0) * count

        return total_weight, cylinders

    def _update_remaining_capacity(
        self, capacity: VehicleCapacity, orders: List[Order]
    ) -> VehicleCapacity:
        """Update remaining capacity after assigning orders"""
        total_weight, cylinders = self._calculate_order_totals(orders)

        return VehicleCapacity(
            max_weight_kg=capacity.max_weight_kg - total_weight,
            max_cylinders_50kg=capacity.max_cylinders_50kg - cylinders.get("50kg", 0),
            max_cylinders_20kg=capacity.max_cylinders_20kg - cylinders.get("20kg", 0),
            max_cylinders_16kg=capacity.max_cylinders_16kg - cylinders.get("16kg", 0),
            max_cylinders_10kg=capacity.max_cylinders_10kg - cylinders.get("10kg", 0),
            max_cylinders_4kg=capacity.max_cylinders_4kg - cylinders.get("4kg", 0),
        )

    def _calculate_order_totals(
        self, orders: List[Order]
    ) -> Tuple[float, Dict[str, int]]:
        """Calculate total weight and cylinder counts for multiple orders"""
        total_weight = 0
        total_cylinders = defaultdict(int)

        for order in orders:
            weight, cylinders = self._calculate_order_weight_and_cylinders(order)
            total_weight += weight
            for size, count in cylinders.items():
                total_cylinders[size] += count

        return total_weight, dict(total_cylinders)

    def _estimate_service_duration(self, order: Order) -> int:
        """Estimate service duration in minutes based on order size"""
        base_duration = 5  # Base 5 minutes

        # Add time based on number of cylinders
        total_cylinders = (
            (order.qty_50kg or 0)
            + (order.qty_20kg or 0)
            + (order.qty_16kg or 0)
            + (order.qty_10kg or 0)
            + (order.qty_4kg or 0)
        )

        # 2 minutes per cylinder
        cylinder_time = total_cylinders * 2

        # Add extra time for large cylinders
        large_cylinder_time = (order.qty_50kg or 0) * 3

        return base_duration + cylinder_time + large_cylinder_time

    def _format_order_products(self, order: Order) -> str:
        """Format order products for display"""
        products = []

        if order.qty_50kg:
            products.append(f"50kg×{order.qty_50kg}")
        if order.qty_20kg:
            products.append(f"20kg×{order.qty_20kg}")
        if order.qty_16kg:
            products.append(f"16kg×{order.qty_16kg}")
        if order.qty_10kg:
            products.append(f"10kg×{order.qty_10kg}")
        if order.qty_4kg:
            products.append(f"4kg×{order.qty_4kg}")

        return ", ".join(products)

    def _calculate_optimization_score(
        self, route_result: Any, orders: List[Order], constraints: DriverConstraints
    ) -> float:
        """Calculate optimization score (0 - 100)"""
        score = 100.0

        # Penalize for long routes
        if route_result.total_duration_seconds > 28800:  # 8 hours
            score -= 10

        # Penalize for very long distances
        if route_result.total_distance_meters > 200000:  # 200km
            score -= 10

        # Bonus for urgent orders delivered early
        urgent_count = sum(1 for o in orders if o.is_urgent)
        if urgent_count > 0:
            score += min(urgent_count * 2, 10)

        return max(0, min(100, score))

    def _calculate_remaining_capacity(
        self, initial_capacity: VehicleCapacity, orders: List[Order]
    ) -> VehicleCapacity:
        """Calculate remaining capacity after orders"""
        return self._update_remaining_capacity(initial_capacity, orders)

    async def _balance_driver_workload(
        self, routes: List[OptimizedRoute]
    ) -> List[OptimizedRoute]:
        """Balance workload across drivers"""
        # Simple balancing: ensure no driver has >20% more work than average
        if len(routes) < 2:
            return routes

        avg_duration = sum(r.total_duration_minutes for r in routes) / len(routes)
        max_allowed = avg_duration * 1.2

        # TODO: Implement actual workload balancing
        # For now, just log imbalances
        for route in routes:
            if route.total_duration_minutes > max_allowed:
                logger.warning(
                    f"Driver {route.driver_id} has imbalanced workload: "
                    f"{route.total_duration_minutes:.0f} minutes vs "
                    f"{avg_duration:.0f} average"
                )

        return routes

    def _create_fallback_route(
        self,
        driver: User,
        orders: List[Order],
        constraints: DriverConstraints,
        route_date: datetime,
    ) -> OptimizedRoute:
        """Create a simple unoptimized route as fallback"""
        # Sort orders by area and address
        sorted_orders = sorted(
            orders, key=lambda o: (o.customer.area or "", o.customer.address)
        )

        stops = []
        for i, order in enumerate(sorted_orders):
            stops.append(
                {
                    "sequence": i + 1,
                    "order_id": order.id,
                    "customer_name": order.customer.short_name,
                    "address": order.delivery_address or order.customer.address,
                    "products": self._format_order_products(order),
                    "estimated_arrival": None,
                    "service_duration": self._estimate_service_duration(order),
                    "priority": 5 if order.is_urgent else 1,
                    "notes": order.delivery_notes,
                }
            )

        total_weight, cylinder_counts = self._calculate_order_totals(orders)

        # Rough estimates
        total_stops = len(orders)
        avg_distance_between_stops = 5  # 5km average
        avg_time_per_stop = 20  # 20 minutes average

        total_distance = total_stops * avg_distance_between_stops
        total_duration = total_stops * avg_time_per_stop

        start_time = datetime.combine(route_date.date(), constraints.start_time)
        end_time = start_time + timedelta(minutes=total_duration)

        return OptimizedRoute(
            driver_id=driver.id,
            route_date=route_date,
            stops=stops,
            total_distance_km=total_distance,
            total_duration_minutes=total_duration,
            total_weight_kg=total_weight,
            cylinder_counts=cylinder_counts,
            estimated_start_time=start_time,
            estimated_end_time=end_time,
            optimization_score=50.0,  # Fallback route gets lower score
            warnings=["使用備用路線規劃，建議手動調整"],
        )
