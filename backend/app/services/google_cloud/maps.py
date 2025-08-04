"""
Placeholder Google Maps Route Optimization Service
This will be replaced with actual Google Maps Route Optimization API
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, time
import random
import math
from app.models.route import Route
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.core.database import get_async_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging

logger = logging.getLogger(__name__)


class RouteOptimizationService:
    """
    Placeholder service for route optimization using mock algorithms
    In production, this will use Google Maps Route Optimization API
    """

    def __init__(self):
        self.api_key = "placeholder-api-key"
        # Lucky Gas depot location (placeholder coordinates in Taipei)
        self.depot_location = {
            "lat": 25.0330,
            "lng": 121.5654,
            "address": "台北市大安區忠孝東路三段1號",
        }

    async def optimize_delivery_routes(
        self, orders: List[Order], vehicles: List[Vehicle], optimization_date: datetime
    ) -> Dict[str, Any]:
        """
        Optimize delivery routes for given orders and vehicles
        Returns optimized route assignments
        """
        logger.info(
            f"Optimizing routes for {len(orders)} orders and {len(vehicles)} vehicles"
        )

        # Group orders by area for basic optimization
        area_groups = self._group_orders_by_area(orders)

        # Assign vehicles to areas
        route_assignments = []
        unassigned_orders = []

        vehicle_index = 0
        for area, area_orders in area_groups.items():
            if vehicle_index >= len(vehicles):
                # No more vehicles available
                unassigned_orders.extend(area_orders)
                continue

            vehicle = vehicles[vehicle_index]

            # Create route for this vehicle
            route_data = await self._create_optimized_route(
                vehicle=vehicle,
                orders=area_orders,
                route_date=optimization_date,
                area=area,
            )

            route_assignments.append(route_data)
            vehicle_index += 1

        # Calculate optimization metrics
        total_distance = sum(route["total_distance_km"] for route in route_assignments)
        total_duration = sum(
            route["estimated_duration_minutes"] for route in route_assignments
        )

        return {
            "optimization_id": f"opt-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "routes": route_assignments,
            "unassigned_orders": [
                {"order_id": o.id, "reason": "no_vehicle_available"}
                for o in unassigned_orders
            ],
            "metrics": {
                "total_routes": len(route_assignments),
                "total_orders": len(orders),
                "assigned_orders": len(orders) - len(unassigned_orders),
                "total_distance_km": round(total_distance, 2),
                "total_duration_hours": round(total_duration / 60, 2),
                "optimization_score": 0.85,  # Mock optimization score
                "cost_savings_percentage": 18.5,  # Mock savings
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _group_orders_by_area(self, orders: List[Order]) -> Dict[str, List[Order]]:
        """Group orders by delivery area"""
        area_groups = {}
        for order in orders:
            area = (
                order.customer.area
                if order.customer and order.customer.area
                else "未分區"
            )
            if area not in area_groups:
                area_groups[area] = []
            area_groups[area].append(order)
        return area_groups

    async def _create_optimized_route(
        self, vehicle: Vehicle, orders: List[Order], route_date: datetime, area: str
    ) -> Dict[str, Any]:
        """Create an optimized route for a vehicle and set of orders"""

        # Sort orders by mock optimization (in real implementation, use actual algorithm)
        optimized_order = self._optimize_order_sequence(orders)

        # Calculate route metrics
        stops = []
        current_location = self.depot_location
        total_distance = 0
        total_duration = 0

        for idx, order in enumerate(optimized_order):
            # Mock distance calculation
            distance = self._calculate_distance(
                current_location, self._get_order_location(order)
            )

            # Estimate duration (15 min per stop + travel time)
            travel_time = distance * 2  # 2 min per km (mock)
            service_time = 15  # 15 min per delivery

            stop = {
                "sequence": idx + 1,
                "order_id": order.id,
                "customer_name": (
                    order.customer.short_name
                    if order.customer
                    else f"Customer {order.customer_id}"
                ),
                "address": order.delivery_address
                or (order.customer.address if order.customer else ""),
                "location": self._get_order_location(order),
                "time_window": {
                    "start": order.delivery_time_start or "09:00",
                    "end": order.delivery_time_end or "17:00",
                },
                "estimated_arrival": (
                    route_date + timedelta(minutes=total_duration + travel_time)
                ).isoformat(),
                "estimated_duration_minutes": service_time,
                "distance_from_previous_km": round(distance, 2),
                "products": self._get_order_products(order),
            }

            stops.append(stop)
            total_distance += distance
            total_duration += travel_time + service_time
            current_location = self._get_order_location(order)

        # Add return to depot
        return_distance = self._calculate_distance(
            current_location, self.depot_location
        )
        total_distance += return_distance
        total_duration += return_distance * 2

        return {
            "route_id": f"R-{route_date.strftime('%Y%m%d')}-{vehicle.id:03d}",
            "vehicle_id": vehicle.id,
            "vehicle_plate": vehicle.plate_number,
            "driver_id": vehicle.driver_id if hasattr(vehicle, "driver_id") else None,
            "area": area,
            "date": route_date.date().isoformat(),
            "stops": stops,
            "metrics": {
                "total_stops": len(stops),
                "total_distance_km": round(total_distance, 2),
                "estimated_duration_minutes": round(total_duration),
                "estimated_start_time": "08:00",
                "estimated_end_time": (
                    datetime.combine(route_date.date(), time(8, 0))
                    + timedelta(minutes=total_duration)
                ).strftime("%H:%M"),
                "vehicle_utilization": min(
                    0.95,
                    (
                        len(orders)
                        * 20
                        / (
                            vehicle.max_cylinders_50kg * 50
                            + vehicle.max_cylinders_20kg * 20
                            + vehicle.max_cylinders_16kg * 16
                            + vehicle.max_cylinders_10kg * 10
                            + vehicle.max_cylinders_4kg * 4
                        )
                        if any(
                            [
                                vehicle.max_cylinders_50kg,
                                vehicle.max_cylinders_20kg,
                                vehicle.max_cylinders_16kg,
                                vehicle.max_cylinders_10kg,
                                vehicle.max_cylinders_4kg,
                            ]
                        )
                        else 0.5
                    ),
                ),  # Mock utilization
            },
        }

    def _optimize_order_sequence(self, orders: List[Order]) -> List[Order]:
        """
        Mock optimization using nearest neighbor algorithm
        In production, this would use Google's optimization
        """
        if not orders:
            return []

        optimized = []
        remaining = orders.copy()
        current_location = self.depot_location

        while remaining:
            # Find nearest unvisited order
            nearest_idx = 0
            nearest_distance = float("inf")

            for idx, order in enumerate(remaining):
                distance = self._calculate_distance(
                    current_location, self._get_order_location(order)
                )
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_idx = idx

            # Add nearest order to optimized list
            nearest_order = remaining.pop(nearest_idx)
            optimized.append(nearest_order)
            current_location = self._get_order_location(nearest_order)

        return optimized

    def _calculate_distance(self, loc1: Dict, loc2: Dict) -> float:
        """
        Calculate distance between two locations using Haversine formula
        Returns distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1, lon1 = math.radians(loc1["lat"]), math.radians(loc1["lng"])
        lat2, lon2 = math.radians(loc2["lat"]), math.radians(loc2["lng"])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _get_order_location(self, order: Order) -> Dict[str, float]:
        """Get mock location for an order"""
        # In production, this would geocode the actual address
        # For now, generate random location near depot
        base_lat = self.depot_location["lat"]
        base_lng = self.depot_location["lng"]

        # Random offset within ~10km
        lat_offset = random.uniform(-0.09, 0.09)
        lng_offset = random.uniform(-0.09, 0.09)

        return {"lat": base_lat + lat_offset, "lng": base_lng + lng_offset}

    def _get_order_products(self, order: Order) -> List[Dict[str, Any]]:
        """Get product summary for an order"""
        products = []

        # Check if order has new flexible products
        if hasattr(order, "order_items") and order.order_items:
            for item in order.order_items:
                products.append(
                    {
                        "product_name": (
                            item.gas_product.display_name
                            if item.gas_product
                            else f"Product {item.gas_product_id}"
                        ),
                        "quantity": item.quantity,
                        "size_kg": item.gas_product.size_kg if item.gas_product else 0,
                    }
                )
        else:
            # Legacy cylinder quantities
            if order.qty_50kg > 0:
                products.append(
                    {
                        "product_name": "50kg 桶裝瓦斯",
                        "quantity": order.qty_50kg,
                        "size_kg": 50,
                    }
                )
            if order.qty_20kg > 0:
                products.append(
                    {
                        "product_name": "20kg 桶裝瓦斯",
                        "quantity": order.qty_20kg,
                        "size_kg": 20,
                    }
                )
            if order.qty_16kg > 0:
                products.append(
                    {
                        "product_name": "16kg 桶裝瓦斯",
                        "quantity": order.qty_16kg,
                        "size_kg": 16,
                    }
                )
            if order.qty_10kg > 0:
                products.append(
                    {
                        "product_name": "10kg 桶裝瓦斯",
                        "quantity": order.qty_10kg,
                        "size_kg": 10,
                    }
                )
            if order.qty_4kg > 0:
                products.append(
                    {
                        "product_name": "4kg 桶裝瓦斯",
                        "quantity": order.qty_4kg,
                        "size_kg": 4,
                    }
                )

        return products

    async def get_route_navigation(self, route_id: int) -> Optional[Dict[str, Any]]:
        """
        Get turn-by-turn navigation for a route
        In production, this would use Google Maps Directions API
        """
        # Mock navigation data
        return {
            "route_id": route_id,
            "navigation_steps": [
                {
                    "instruction": "從倉庫出發，向東行駛至忠孝東路",
                    "distance": "0.5 km",
                    "duration": "2 分鐘",
                },
                {
                    "instruction": "在忠孝東路左轉",
                    "distance": "2.3 km",
                    "duration": "8 分鐘",
                },
                {
                    "instruction": "抵達第一個配送點",
                    "distance": "0 km",
                    "duration": "0 分鐘",
                },
            ],
            "polyline": "placeholder_polyline_data",  # In production, actual polyline
            "bounds": {
                "northeast": {"lat": 25.0430, "lng": 121.5754},
                "southwest": {"lat": 25.0230, "lng": 121.5554},
            },
        }

    async def update_driver_location(
        self, driver_id: int, latitude: float, longitude: float
    ) -> Dict[str, Any]:
        """
        Update driver's current location
        In production, this would update real-time tracking
        """
        return {
            "driver_id": driver_id,
            "location": {"lat": latitude, "lng": longitude},
            "timestamp": datetime.utcnow().isoformat(),
            "speed_kmh": random.uniform(20, 60),
            "heading": random.randint(0, 359),
            "accuracy_meters": 10,
        }

    async def calculate_eta(
        self, current_location: Tuple[float, float], destination: Tuple[float, float]
    ) -> Dict[str, Any]:
        """
        Calculate ETA from current location to destination
        """
        distance = self._calculate_distance(
            {"lat": current_location[0], "lng": current_location[1]},
            {"lat": destination[0], "lng": destination[1]},
        )

        # Estimate based on average speed
        avg_speed_kmh = 30
        duration_minutes = (distance / avg_speed_kmh) * 60

        return {
            "distance_km": round(distance, 2),
            "duration_minutes": round(duration_minutes),
            "eta": (
                datetime.utcnow() + timedelta(minutes=duration_minutes)
            ).isoformat(),
            "traffic_condition": random.choice(["light", "moderate", "heavy"]),
        }


# Singleton instance
route_optimization_service = RouteOptimizationService()
