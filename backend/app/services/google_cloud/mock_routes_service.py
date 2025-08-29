"""
Mock Google Routes Service for Development
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt

from app.core.config import settings
from app.services.google_cloud.routes_service import GoogleRoutesService
from app.services.optimization.ortools_optimizer import VRPStop

logger = logging.getLogger(__name__)


class MockGoogleRoutesService(GoogleRoutesService):
    """
    Realistic mock implementation of Google Routes API for development
    Provides deterministic results for testing while simulating real API behavior
    """

    def __init__(self):
        # Don't call parent __init__ to avoid API key requirements
        self.depot_location = (settings.DEPOT_LAT, settings.DEPOT_LNG)
        self.mock_delays = {"min": 0.05, "max": 0.3}  # 50ms minimum  # 300ms maximum

        # Realistic encoded polylines for Taiwan routes
        self.mock_polylines = [
            "ipkcFfichVnP@j@kBiD{FqCcBuBqAsAqE_DmGyIoB}C",
            "u{~vFvyys@fS]tBgCtC_DiD{EmFsHaIiKcJuM",
            "_gjaF~jbs@qBmGyCaIcDwJuEoMaFwNgGqQeHcS",
            "mjiaF~pbs@iBcF_CgGaDiIcEkLaFoNgGsQeH_T",
            "ypkcFnichV~MnBfC`DpBbCxArBdCfDvDjF|FvH",
        ]

        # Taiwan - specific traffic patterns
        self.traffic_multipliers = {
            "morning_rush": 1.5,  # 7 - 9 AM
            "evening_rush": 1.6,  # 5 - 7 PM
            "lunch": 1.2,  # 12 - 1 PM
            "night": 0.8,  # 10 PM - 6 AM
            "normal": 1.0,
        }

        # Area - specific characteristics
        self.area_factors = {
            "信義區": {"speed": 25, "congestion": 1.3},
            "大安區": {"speed": 30, "congestion": 1.2},
            "中山區": {"speed": 28, "congestion": 1.25},
            "松山區": {"speed": 32, "congestion": 1.15},
            "內湖區": {"speed": 35, "congestion": 1.1},
            "士林區": {"speed": 30, "congestion": 1.2},
            "北投區": {"speed": 33, "congestion": 1.1},
            "文山區": {"speed": 28, "congestion": 1.2},
            "南港區": {"speed": 35, "congestion": 1.1},
            "萬華區": {"speed": 25, "congestion": 1.3},
            "中正區": {"speed": 28, "congestion": 1.25},
            "大同區": {"speed": 26, "congestion": 1.3},
        }

    def _get_traffic_multiplier(self) -> float:
        """Get traffic multiplier based on current time"""
        hour = datetime.now().hour

        if 7 <= hour < 9:
            return self.traffic_multipliers["morning_rush"]
        elif 17 <= hour < 19:
            return self.traffic_multipliers["evening_rush"]
        elif 12 <= hour < 13:
            return self.traffic_multipliers["lunch"]
        elif hour >= 22 or hour < 6:
            return self.traffic_multipliers["night"]
        else:
            return self.traffic_multipliers["normal"]

    def _calculate_realistic_time(
        self, distance_km: float, area: str = "信義區"
    ) -> float:
        """Calculate realistic travel time based on distance and area"""
        area_info = self.area_factors.get(area, {"speed": 30, "congestion": 1.2})
        base_speed = area_info["speed"]
        congestion = area_info["congestion"]
        traffic = self._get_traffic_multiplier()

        # Effective speed considering all factors
        effective_speed = base_speed / (congestion * traffic)

        # Time in minutes
        time_minutes = (distance_km / effective_speed) * 60

        # Add stop time (traffic lights, etc.)
        # Approximately 1 traffic light per 0.5km in city
        num_stops = int(distance_km / 0.5)
        stop_time = num_stops * 0.5  # 30 seconds per stop

        return time_minutes + stop_time

    async def optimize_route(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int = 100,
        time_windows: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Mock route optimization with realistic Taiwan traffic simulation"""
        # Simulate API latency
        delay = random.uniform(self.mock_delays["min"], self.mock_delays["max"])
        await asyncio.sleep(delay)

        logger.info(f"Mock route optimization for {len(stops)} stops")

        if not stops:
            return {
                "stops": [],
                "total_distance": 0,
                "total_duration": "0s",
                "polyline": "",
                "warnings": ["No stops to optimize"],
                "optimized": True,
            }

        # Use nearest neighbor algorithm with priority consideration
        optimized_stops = self._nearest_neighbor_with_priority(depot, stops)

        # Calculate route metrics
        total_distance = 0
        total_duration = 0
        current_location = depot

        for i, stop in enumerate(optimized_stops):
            # Calculate distance from previous location
            distance = self._calculate_distance(
                current_location[0], current_location[1], stop["lat"], stop["lng"]
            )
            total_distance += distance

            # Calculate realistic travel time
            area = stop.get("area", "信義區")
            travel_time = self._calculate_realistic_time(distance, area)
            service_time = stop.get("service_time", 10)

            total_duration += travel_time + service_time

            # Update stop information
            stop["stop_sequence"] = i + 1
            stop["distance_from_previous"] = round(distance, 2)
            stop["travel_time_minutes"] = round(travel_time, 1)
            stop["estimated_arrival"] = (
                datetime.now() + timedelta(minutes=total_duration - service_time)
            ).isoformat()

            current_location = (stop["lat"], stop["lng"])

        # Add return to depot
        if optimized_stops:
            return_distance = self._calculate_distance(
                current_location[0], current_location[1], depot[0], depot[1]
            )
            total_distance += return_distance
            return_time = self._calculate_realistic_time(return_distance)
            total_duration += return_time

        # Select appropriate polyline
        polyline_index = len(stops) % len(self.mock_polylines)

        return {
            "stops": optimized_stops,
            "total_distance": round(total_distance * 1000, 0),  # Convert to meters
            "total_duration": f"{int(total_duration * 60)}s",  # Convert to seconds
            "polyline": self.mock_polylines[polyline_index],
            "warnings": ["Using mock optimization service (development mode)"],
            "optimized": True,
            "optimization_details": {
                "algorithm": "mock_nearest_neighbor_with_priority",
                "computation_time_ms": int(delay * 1000),
                "traffic_multiplier": self._get_traffic_multiplier(),
                "timestamp": datetime.now().isoformat(),
            },
        }

    def _nearest_neighbor_with_priority(
        self, depot: Tuple[float, float], stops: List[Dict]
    ) -> List[Dict]:
        """
        Nearest neighbor algorithm that considers priority
        High priority stops are visited first
        """
        remaining = stops.copy()
        route = []
        current_location = depot

        # First, handle high priority stops
        high_priority = [s for s in remaining if s.get("priority", 0) > 5]
        normal_priority = [s for s in remaining if s.get("priority", 0) <= 5]

        # Sort high priority by distance from depot
        high_priority.sort(
            key=lambda s: self._calculate_distance(
                depot[0], depot[1], s["lat"], s["lng"]
            )
        )

        # Add high priority stops first
        for stop in high_priority:
            route.append(stop)
            remaining.remove(stop)

        # Then add remaining stops using nearest neighbor
        current_location = route[-1] if route else depot
        current_location = (
            (current_location["lat"], current_location["lng"]) if route else depot
        )

        while remaining:
            nearest = min(
                remaining,
                key=lambda s: self._calculate_distance(
                    current_location[0], current_location[1], s["lat"], s["lng"]
                ),
            )
            route.append(nearest)
            remaining.remove(nearest)
            current_location = (nearest["lat"], nearest["lng"])

        return route

    async def optimize_multiple_routes(
        self, orders: List[Any], drivers: List[Dict], date: datetime
    ) -> List[Dict]:
        """Mock multiple route optimization"""
        # Simulate API latency
        delay = random.uniform(0.2, 0.5)
        await asyncio.sleep(delay)

        logger.info(
            f"Mock multiple route optimization: {len(orders)} orders, "
            f"{len(drivers)} drivers"
        )

        if not orders or not drivers:
            return []

        # Simple distribution: divide orders among drivers
        orders_per_driver = len(orders) // len(drivers)
        extra_orders = len(orders) % len(drivers)

        routes = []
        order_index = 0

        for i, driver in enumerate(drivers):
            # Calculate number of orders for this driver
            num_orders = orders_per_driver + (1 if i < extra_orders else 0)
            driver_orders = orders[order_index : order_index + num_orders]
            order_index += num_orders

            if not driver_orders:
                continue

            # Convert orders to stops
            stops = []
            for order in driver_orders:
                if hasattr(order, "customer") and order.customer:
                    stop = {
                        "order_id": order.id,
                        "customer_id": order.customer_id,
                        "customer_name": order.customer.short_name,
                        "address": order.delivery_address or order.customer.address,
                        "lat": order.customer.latitude
                        or self.depot_location[0] + random.uniform(-0.1, 0.1),
                        "lng": order.customer.longitude
                        or self.depot_location[1] + random.uniform(-0.1, 0.1),
                        "area": order.customer.area or "信義區",
                        "priority": 10 if order.is_urgent else 5,
                        "service_time": self._estimate_service_time(order),
                        "products": self._get_order_products(order),
                    }
                    stops.append(stop)

            # Optimize this route
            optimized = await self.optimize_route(
                depot=self.depot_location, stops=stops, vehicle_capacity=100
            )

            # Build route data
            route_data = {
                "route_number": f"R{date.strftime('%Y % m % d')}-{i + 1:02d}",
                "driver_id": driver["id"],
                "driver_name": driver.get("name", f"Driver {i + 1}"),
                "vehicle_id": driver.get("vehicle_id", i + 1),
                "date": date.isoformat(),
                "status": "optimized",
                "area": self._determine_primary_area(
                    [s["area"] for s in stops if "area" in s]
                ),
                "stops": optimized["stops"],
                "total_stops": len(optimized["stops"]),
                "total_distance_km": optimized["total_distance"] / 1000,
                "estimated_duration_minutes": int(
                    optimized["total_duration"].rstrip("s")
                )
                / 60,
                "polyline": optimized["polyline"],
                "optimized": True,
                "optimization_method": "mock_distribution",
            }
            routes.append(route_data)

        return routes

    def _estimate_service_time(self, order) -> int:
        """Estimate service time for an order"""
        base_time = 5
        cylinder_time = 0

        # Add time based on cylinder count
        for size in [50, 20, 16, 10, 4]:
            qty_field = f"qty_{size}kg"
            if hasattr(order, qty_field):
                qty = getattr(order, qty_field, 0)
                # Larger cylinders take more time
                time_per_cylinder = 3 if size >= 20 else 2
                cylinder_time += qty * time_per_cylinder

        return base_time + cylinder_time

    def _get_order_products(self, order) -> Dict[str, int]:
        """Extract product quantities from order"""
        products = {}

        for size in [50, 20, 16, 10, 4]:
            qty_field = f"qty_{size}kg"
            if hasattr(order, qty_field):
                qty = getattr(order, qty_field, 0)
                if qty > 0:
                    products[f"{size}kg"] = qty

        return products

    def _determine_primary_area(self, areas: List[str]) -> str:
        """Determine primary area from list of areas"""
        if not areas:
            return "Unknown"

        # Count occurrences
        area_counts = {}
        for area in areas:
            area_counts[area] = area_counts.get(area, 0) + 1

        # Return most common area
        return max(area_counts, key=area_counts.get)

    async def _get_google_directions(
        self, depot: Tuple[float, float], stops: List[VRPStop]
    ) -> Dict:
        """Mock Google directions for visualization"""
        # Simulate quick API response
        await asyncio.sleep(random.uniform(0.02, 0.05))

        if not stops:
            return {"distance": 0, "duration": 0, "polyline": ""}

        total_distance = 0
        total_duration = 0

        # Calculate route metrics
        current_location = depot
        for stop in stops:
            distance = self._calculate_distance(
                current_location[0], current_location[1], stop.latitude, stop.longitude
            )
            total_distance += distance

            # Use area if available
            area = getattr(stop, "area", "信義區")
            travel_time = self._calculate_realistic_time(distance, area)
            total_duration += travel_time + stop.service_time

            current_location = (stop.latitude, stop.longitude)

        # Return to depot
        return_distance = self._calculate_distance(
            current_location[0], current_location[1], depot[0], depot[1]
        )
        total_distance += return_distance
        total_duration += self._calculate_realistic_time(return_distance)

        # Select polyline based on stop count
        polyline_index = len(stops) % len(self.mock_polylines)

        return {
            "distance": round(total_distance, 2),
            "duration": round(total_duration, 0),
            "polyline": self.mock_polylines[polyline_index],
        }

    def _calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = (
            sin(delta_lat / 2) ** 2
            + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        )
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c
