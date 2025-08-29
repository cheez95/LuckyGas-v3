"""
Google Routes API Service for route optimization
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp

from app.core.config import settings
from app.core.google_cloud_config import get_gcp_config
from app.core.metrics import route_optimization_histogram
from app.models.order import Order
from app.services.optimization.ortools_optimizer import (
    VRPStop,
    VRPVehicle,
    ortools_optimizer,
)

logger = logging.getLogger(__name__)


@dataclass
class DeliveryLocation:
    """Represents a delivery location"""

    order_id: int
    customer_id: int
    customer_name: str
    address: str
    latitude: float
    longitude: float
    priority: int = 0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    service_duration_minutes: int = 10
    products: Dict[str, int] = None


class GoogleRoutesService:
    """
    Service for route optimization using Google Routes API
    """

    def __init__(self):
        self.gcp_config = get_gcp_config()
        self.api_key = self.gcp_config.maps_api_key
        self.base_url = "https://routes.googleapis.com / directions / v2:computeRoutes"
        self.matrix_url = (
            "https://routes.googleapis.com / distanceMatrix / v2:computeRouteMatrix"
        )
        self.optimization_url = "https://routes.googleapis.com / v1 / projects/{}/locations/{}/routeOptimization:optimizeTours"
        self.depot_location = (settings.DEPOT_LAT, settings.DEPOT_LNG)

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.backoff_multiplier = 2.0

        # Rate limiting configuration
        self.requests_per_second = 10
        self.last_request_time = 0
        self._request_lock = asyncio.Lock()

    async def optimize_route(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int = 100,
        time_windows: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Optimize delivery route using Google Routes API with retry logic and rate limiting
        """
        if not self.api_key:
            logger.warning(
                "Google Maps API key not configured, returning unoptimized route"
            )
            return self._create_unoptimized_route(depot, stops)

        # Apply rate limiting
        await self._apply_rate_limit()

        # Build optimization request
        request_body = self._build_optimization_request(
            depot, stops, vehicle_capacity, time_windows
        )

        # Execute with retry logic
        for attempt in range(self.max_retries):
            try:
                result = await self._execute_api_request(
                    self.base_url,
                    request_body,
                    "routes.optimizedIntermediateWaypointIndex, routes.duration, routes.distanceMeters, routes.polyline, routes.legs",
                )

                if result:
                    return self._process_route_response(result, stops)

            except aiohttp.ClientError as e:
                logger.warning(
                    f"API request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(
                        self.retry_delay * (self.backoff_multiplier**attempt)
                    )
                else:
                    logger.error("All retry attempts failed for route optimization")

            except Exception as e:
                logger.error(f"Unexpected error in route optimization: {e}")
                break

        # Fallback to unoptimized route
        return self._create_unoptimized_route(depot, stops)

    def _build_optimization_request(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int,
        time_windows: Optional[Dict],
    ) -> Dict:
        """Build request body for Routes API with enhanced parameters"""

        # Create waypoints with metadata
        waypoints = []

        for stop in stops:
            waypoint = {
                "location": {
                    "latLng": {"latitude": stop["lat"], "longitude": stop["lng"]}
                },
                "sideOfRoad": True,  # Allow stopping on either side
                "vehicleStopover": True,  # This is a delivery stop
            }

            # Add place ID if available for better geocoding
            if stop.get("place_id"):
                waypoint["placeId"] = stop["place_id"]

            waypoints.append(waypoint)

        # Build request with Taiwan - specific optimizations
        request = {
            "origin": {
                "location": {"latLng": {"latitude": depot[0], "longitude": depot[1]}},
                "sideOfRoad": True,
            },
            "destination": {
                "location": {"latLng": {"latitude": depot[0], "longitude": depot[1]}},
                "sideOfRoad": True,
            },
            "intermediates": waypoints,
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE_OPTIMAL",  # Best for urban delivery
            "optimizeWaypointOrder": True,
            "languageCode": "zh - TW",
            "regionCode": "TW",
            "units": "METRIC",
            "computeAlternativeRoutes": False,
            "routeModifiers": {
                "avoidTolls": False,  # Taiwan has few tolls
                "avoidHighways": False,  # Highways often faster in Taiwan
                "avoidFerries": True,  # Avoid ferries for reliability
                "avoidIndoor": True,  # Avoid indoor navigation
            },
            "extraComputations": ["TOLLS", "FUEL_CONSUMPTION"],  # Get additional data
            "requestedReferenceRoutes": [
                "FUEL_EFFICIENT"
            ],  # Compare with fuel - efficient route
        }

        # Add departure time for traffic - aware routing
        if time_windows:
            departure_time = time_windows.get("departure_time")
            if departure_time:
                request["departureTime"] = departure_time

        return request

    def _process_route_response(
        self, response: Dict, original_stops: List[Dict]
    ) -> Dict:
        """Process the API response with enhanced data extraction"""

        if not response.get("routes"):
            return self._create_unoptimized_route(self.depot_location, original_stops)

        route = response["routes"][0]

        # Get optimized order
        optimized_order = []
        if "optimizedIntermediateWaypointIndex" in route:
            optimized_indices = route["optimizedIntermediateWaypointIndex"]
            optimized_order = [original_stops[i] for i in optimized_indices]
        else:
            optimized_order = original_stops

        # Process legs for detailed timing and distance
        legs = route.get("legs", [])
        cumulative_duration = 0
        cumulative_distance = 0

        # Add detailed information to each stop
        for i, stop in enumerate(optimized_order):
            stop["stop_sequence"] = i + 1

            # Get leg information (depot to first stop, stop to stop, last stop to depot)
            if i < len(legs) - 1:  # Exclude the last leg (return to depot)
                leg = legs[i]
                leg_duration = self._parse_duration(leg.get("duration", "0s"))
                leg_distance = leg.get("distanceMeters", 0)

                cumulative_duration += leg_duration
                cumulative_distance += leg_distance

                stop["leg_distance_meters"] = leg_distance
                stop["leg_duration_minutes"] = leg_duration
                stop["cumulative_distance_meters"] = cumulative_distance
                stop["estimated_arrival"] = self._calculate_arrival_time_from_duration(
                    cumulative_duration
                )

                # Add traffic information if available
                if "staticDuration" in leg:
                    static_duration = self._parse_duration(leg["staticDuration"])
                    stop["traffic_delay_minutes"] = leg_duration - static_duration
            else:
                # For the last stop, estimate based on service time
                stop["estimated_arrival"] = self._calculate_arrival_time_from_duration(
                    cumulative_duration + stop.get("service_time", 10)
                )

        # Extract additional route information
        route_info = {
            "stops": optimized_order,
            "total_distance": route.get("distanceMeters", 0),
            "total_duration": route.get("duration", "0s"),
            "total_duration_minutes": self._parse_duration(route.get("duration", "0s")),
            "polyline": route.get("polyline", {}).get("encodedPolyline", ""),
            "warnings": route.get("warnings", []),
            "optimized": True,
            "optimization_savings": self._calculate_optimization_savings(
                route, response
            ),
        }

        # Add fuel consumption if available
        if "fuelConsumptionMicroliters" in route:
            route_info["fuel_consumption_liters"] = (
                route["fuelConsumptionMicroliters"] / 1_000_000
            )

        # Add toll information if available
        if "tolls" in route:
            route_info["toll_info"] = route["tolls"]

        return route_info

    def _create_unoptimized_route(
        self, depot: Tuple[float, float], stops: List[Dict]
    ) -> Dict:
        """Create a basic unoptimized route as fallback"""

        # Simple distance - based sorting
        sorted_stops = sorted(
            stops,
            key=lambda s: self._calculate_distance(
                depot[0], depot[1], s["lat"], s["lng"]
            ),
        )

        for i, stop in enumerate(sorted_stops):
            stop["stop_sequence"] = i + 1
            stop["estimated_arrival"] = datetime.now() + timedelta(minutes=30 * (i + 1))

        return {
            "stops": sorted_stops,
            "total_distance": 0,  # Would need to calculate
            "total_duration": "0s",
            "polyline": "",
            "warnings": [
                "Route optimization unavailable - using distance - based sorting"
            ],
            "optimized": False,
        }

    def _calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate approximate distance between two points (Haversine formula)"""
        from math import atan2, cos, radians, sin, sqrt

        R = 6371  # Earth's radius in kilometers

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def _calculate_arrival_time_from_duration(self, duration_minutes: int) -> datetime:
        """Calculate estimated arrival time based on cumulative duration"""
        # Use configured departure time or current time
        base_time = datetime.now()
        return base_time + timedelta(minutes=duration_minutes)

    async def _apply_rate_limit(self):
        """Apply rate limiting to prevent API quota exceeded errors"""
        async with self._request_lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last_request = current_time - self.last_request_time
            min_interval = 1.0 / self.requests_per_second

            if time_since_last_request < min_interval:
                await asyncio.sleep(min_interval - time_since_last_request)

            self.last_request_time = asyncio.get_event_loop().time()

    async def _execute_api_request(
        self, url: str, request_body: Dict, field_mask: str
    ) -> Optional[Dict]:
        """Execute API request with proper error handling"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content - Type": "application / json",
                "X - Goog - Api - Key": self.api_key,
                "X - Goog - FieldMask": field_mask,
            }

            async with session.post(
                url,
                json=request_body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response_text = await response.text()

                if response.status == 200:
                    return json.loads(response_text)
                else:
                    self._handle_api_error(response.status, response_text)
                    return None

    def _handle_api_error(self, status_code: int, error_text: str):
        """Handle different API error codes with appropriate logging"""
        error_data = {}
        try:
            error_data = json.loads(error_text)
        except json.JSONDecodeError:
            pass

        if status_code == 400:
            logger.error(
                f"Bad Request: {error_data.get('error', {}).get('message', error_text)}"
            )
        elif status_code == 401:
            logger.error("Authentication failed: Invalid API key")
        elif status_code == 403:
            logger.error("Access denied: Check API key permissions")
        elif status_code == 429:
            logger.error("Rate limit exceeded: Too many requests")
        elif status_code >= 500:
            logger.error(f"Server error ({status_code}): {error_text}")
        else:
            logger.error(f"API error ({status_code}): {error_text}")

    def _calculate_optimization_savings(
        self, optimized_route: Dict, response: Dict
    ) -> Dict:
        """Calculate savings from optimization compared to reference routes"""
        savings = {
            "distance_saved_meters": 0,
            "time_saved_minutes": 0,
            "fuel_saved_liters": 0,
        }

        # Check if we have reference routes to compare
        if len(response.get("routes", [])) > 1:
            # Compare with fuel - efficient route if available
            for route in response["routes"][1:]:
                if (
                    route.get("routeLabels")
                    and "FUEL_EFFICIENT" in route["routeLabels"]
                ):
                    savings["distance_saved_meters"] = route.get(
                        "distanceMeters", 0
                    ) - optimized_route.get("distanceMeters", 0)
                    savings["time_saved_minutes"] = self._parse_duration(
                        route.get("duration", "0s")
                    ) - self._parse_duration(optimized_route.get("duration", "0s"))
                    if (
                        "fuelConsumptionMicroliters" in route
                        and "fuelConsumptionMicroliters" in optimized_route
                    ):
                        savings["fuel_saved_liters"] = (
                            route["fuelConsumptionMicroliters"]
                            - optimized_route["fuelConsumptionMicroliters"]
                        ) / 1_000_000

        return savings

    async def optimize_multiple_routes(
        self, orders: List[Order], drivers: List[Dict], date: datetime
    ) -> List[Dict]:
        """
        Optimize routes for multiple drivers using OR - Tools VRP solver
        """
        # Convert orders to VRPStop format
        stops = []
        for order in orders:
            if not order.customer:
                continue

            stop = VRPStop(
                order_id=order.id,
                customer_id=order.customer_id,
                customer_name=order.customer.short_name,
                address=order.delivery_address or order.customer.address,
                latitude=order.customer.latitude or self.depot_location[0],
                longitude=order.customer.longitude or self.depot_location[1],
                demand=self._extract_demand(order),
                time_window=self._get_time_window(order),
                service_time=self._estimate_service_time(order),
            )
            stops.append(stop)

        # Convert drivers to VRPVehicle format
        vehicles = []
        for driver in drivers:
            vehicle = VRPVehicle(
                driver_id=driver["id"],
                driver_name=driver["name"],
                capacity={"50kg": 10, "20kg": 20, "16kg": 25, "10kg": 40, "4kg": 50},
                start_location=self.depot_location,
                max_travel_time=480,  # 8 hours
            )
            vehicles.append(vehicle)

        # Optimize using OR - Tools
        logger.info(
            f"Optimizing routes for {len(stops)} orders and {len(drivers)} drivers"
        )

        # Track optimization time
        import time

        start_time = time.time()
        optimized_routes = ortools_optimizer.optimize(stops, vehicles)
        optimization_time = time.time() - start_time

        # Record metrics
        route_optimization_histogram.labels(
            method="OR - Tools VRP", num_stops=str(len(stops))
        ).observe(optimization_time)

        logger.info(f"Route optimization completed in {optimization_time:.2f} seconds")

        # Get turn - by - turn directions from Google Routes API for each route
        route_results = []
        for vehicle_idx, route_stops in optimized_routes.items():
            if not route_stops:
                continue

            # Get Google directions for visualization
            google_route = await self._get_google_directions(
                self.depot_location, route_stops
            )

            # Build route data
            route_data = {
                "route_number": f"R{date.strftime('%Y % m % d')}-{vehicle_idx + 1:02d}",
                "driver_id": vehicles[vehicle_idx].driver_id,
                "vehicle_id": vehicle_idx,
                "date": date.isoformat(),
                "status": "optimized",
                "area": self._determine_area(route_stops),
                "stops": [
                    {
                        "order_id": stop.order_id,
                        "customer_id": stop.customer_id,
                        "customer_name": stop.customer_name,
                        "address": stop.address,
                        "lat": stop.latitude,
                        "lng": stop.longitude,
                        "stop_sequence": idx + 1,
                        "estimated_arrival": self._minutes_to_datetime(
                            date, stop.estimated_arrival
                        ),
                        "service_time": stop.service_time,
                        "products": stop.demand,
                    }
                    for idx, stop in enumerate(route_stops)
                ],
                "total_stops": len(route_stops),
                "total_distance_km": google_route.get("distance", 0),
                "estimated_duration_minutes": google_route.get("duration", 0),
                "polyline": google_route.get("polyline", ""),
                "optimized": True,
                "optimization_method": "OR - Tools VRP",
            }
            route_results.append(route_data)

        return route_results

    async def _optimize_driver_route(
        self, driver: Dict, orders: List[Order], route_number: str, date: datetime
    ) -> Dict:
        """Optimize a single driver's route"""

        # Prepare stops from orders
        stops = []
        for order in orders:
            stop = {
                "order_id": order.id,
                "customer_id": order.customer_id,
                "customer_name": (
                    order.customer.short_name
                    if order.customer
                    else f"Customer {order.customer_id}"
                ),
                "address": order.delivery_address or order.customer.address,
                "lat": order.customer.latitude or settings.DEPOT_LAT,
                "lng": order.customer.longitude or settings.DEPOT_LNG,
                "priority": order.priority,
                "service_time": self._estimate_service_time(order),
                "products": self._get_order_products(order),
            }

            # Add time window if specified
            if hasattr(order.customer, "delivery_time_start"):
                stop["time_window"] = {
                    "start": order.customer.delivery_time_start,
                    "end": order.customer.delivery_time_end,
                }

            stops.append(stop)

        # Optimize route
        optimized = await self.optimize_route(
            depot=self.depot_location,
            stops=stops,
            vehicle_capacity=driver.get("vehicle_capacity", 100),
            time_windows={"start": "08:00", "end": "18:00"},
        )

        # Build response
        return {
            "route_number": route_number,
            "driver_id": driver["id"],
            "vehicle_id": driver.get("vehicle_id"),
            "date": date.isoformat(),
            "status": "optimized",
            "area": self._determine_area(stops),
            "stops": optimized["stops"],
            "total_stops": len(optimized["stops"]),
            "total_distance_km": (
                optimized["total_distance"] / 1000 if optimized["total_distance"] else 0
            ),
            "estimated_duration_minutes": self._parse_duration(
                optimized["total_duration"]
            ),
            "polyline": optimized.get("polyline", ""),
            "warnings": optimized.get("warnings", []),
            "optimized": optimized.get("optimized", False),
        }

    def _cluster_orders_by_location(
        self, orders: List[Order], n_clusters: int
    ) -> List[List[Order]]:
        """
        Cluster orders by geographic location using k - means
        """
        if len(orders) <= n_clusters:
            # If fewer orders than drivers, assign one per driver
            return [[order] for order in orders] + [
                [] for _ in range(n_clusters - len(orders))
            ]

        try:
            import numpy as np
            from sklearn.cluster import KMeans

            # Extract coordinates
            coords = []
            valid_orders = []

            for order in orders:
                if (
                    order.customer
                    and order.customer.latitude
                    and order.customer.longitude
                ):
                    coords.append([order.customer.latitude, order.customer.longitude])
                    valid_orders.append(order)

            if not coords:
                # No valid coordinates, distribute evenly
                orders_per_cluster = len(orders) // n_clusters
                clusters = []
                for i in range(n_clusters):
                    start = i * orders_per_cluster
                    end = (
                        start + orders_per_cluster
                        if i < n_clusters - 1
                        else len(orders)
                    )
                    clusters.append(orders[start:end])
                return clusters

            coords_array = np.array(coords)

            # Perform k - means clustering
            kmeans = KMeans(
                n_clusters=min(n_clusters, len(valid_orders)), random_state=42
            )
            labels = kmeans.fit_predict(coords_array)

            # Group orders by cluster
            clusters = [[] for _ in range(n_clusters)]
            for order, label in zip(valid_orders, labels):
                clusters[label].append(order)

            # Add orders without coordinates to smallest cluster
            for order in orders:
                if order not in valid_orders:
                    min_cluster = min(clusters, key=len)
                    min_cluster.append(order)

            return clusters

        except ImportError:
            # sklearn not available, use simple distribution
            logger.warning(
                "scikit - learn not available, using simple order distribution"
            )
            orders_per_cluster = len(orders) // n_clusters
            clusters = []
            for i in range(n_clusters):
                start = i * orders_per_cluster
                end = start + orders_per_cluster if i < n_clusters - 1 else len(orders)
                clusters.append(orders[start:end])
            return clusters

    def _extract_demand(self, order: Order) -> Dict[str, int]:
        """Extract product demands from order"""
        demand = {}
        for size in [50, 20, 16, 10, 4]:
            qty_field = f"qty_{size}kg"
            if hasattr(order, qty_field):
                qty = getattr(order, qty_field, 0) or 0
                if qty > 0:
                    demand[f"{size}kg"] = qty
        return demand

    def _get_time_window(self, order: Order) -> Tuple[int, int]:
        """Convert delivery time to minutes from day start"""
        if order.customer and order.customer.delivery_time_start:
            start_hour = int(order.customer.delivery_time_start.split(":")[0])
            start_minutes = start_hour * 60
        else:
            start_minutes = 8 * 60  # Default 8 AM

        if order.customer and order.customer.delivery_time_end:
            end_hour = int(order.customer.delivery_time_end.split(":")[0])
            end_minutes = end_hour * 60
        else:
            end_minutes = 18 * 60  # Default 6 PM

        return (start_minutes, end_minutes)

    def _minutes_to_datetime(self, base_date: datetime, minutes: int) -> datetime:
        """Convert minutes from day start to datetime"""
        return datetime.combine(base_date.date(), datetime.min.time()) + timedelta(
            minutes=minutes
        )

    def _estimate_service_time(self, order: Order) -> int:
        """Estimate service time for an order in minutes"""
        base_time = 5  # Base time for any delivery

        # Add time based on cylinder count
        total_cylinders = 0
        for size in [50, 20, 16, 10, 4]:
            qty_field = f"qty_{size}kg"
            if hasattr(order, qty_field):
                qty = getattr(order, qty_field, 0) or 0
                total_cylinders += qty

        # 2 minutes per cylinder
        cylinder_time = total_cylinders * 2

        return base_time + cylinder_time

    def _get_order_products(self, order: Order) -> Dict[str, int]:
        """Get product quantities from order"""
        products = {}

        for size in [50, 20, 16, 10, 4]:
            qty_field = f"qty_{size}kg"
            if hasattr(order, qty_field):
                qty = getattr(order, qty_field, 0) or 0
                if qty > 0:
                    products[f"{size}kg"] = qty

        return products

    async def _get_google_directions(
        self, depot: Tuple[float, float], stops: List[VRPStop]
    ) -> Dict:
        """Get turn - by - turn directions from Google Routes API for visualization"""
        if not self.api_key or not stops:
            return {"distance": 0, "duration": 0, "polyline": ""}

        # Create waypoints for Google Routes API
        waypoints = []
        for stop in stops:
            waypoints.append(
                {
                    "location": {
                        "latLng": {
                            "latitude": stop.latitude,
                            "longitude": stop.longitude,
                        }
                    }
                }
            )

        request_body = {
            "origin": {
                "location": {"latLng": {"latitude": depot[0], "longitude": depot[1]}}
            },
            "destination": {
                "location": {"latLng": {"latitude": depot[0], "longitude": depot[1]}}
            },
            "intermediates": waypoints,
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "optimizeWaypointOrder": False,  # Already optimized by OR - Tools
            "languageCode": "zh - TW",
            "regionCode": "TW",
        }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content - Type": "application / json",
                    "X - Goog - Api - Key": self.api_key,
                    "X - Goog - FieldMask": "routes.duration, routes.distanceMeters, routes.polyline",
                }

                async with session.post(
                    self.base_url, json=request_body, headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("routes"):
                            route = result["routes"][0]
                            return {
                                "distance": route.get("distanceMeters", 0)
                                / 1000,  # Convert to km
                                "duration": self._parse_duration(
                                    route.get("duration", "0s")
                                ),
                                "polyline": route.get("polyline", {}).get(
                                    "encodedPolyline", ""
                                ),
                            }
        except Exception as e:
            logger.error(f"Failed to get Google directions: {e}")

        return {"distance": 0, "duration": 0, "polyline": ""}

    def _determine_area(self, stops: List[Any]) -> str:
        """Determine the primary area for a route"""
        if not stops:
            return "Unknown"

        # In a real implementation, you'd use the customer area field
        # or reverse geocoding to determine the area
        return "Central"  # Placeholder

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string (e.g., '1800s') to minutes"""
        if not duration_str:
            return 0

        # Remove 's' suffix and convert to int
        try:
            seconds = int(duration_str.rstrip("s"))
            return seconds // 60
        except Exception:
            return 0

    async def calculate_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
    ) -> Dict[str, Any]:
        """
        Calculate distance matrix between multiple origins and destinations

        Args:
            origins: List of (lat, lng) tuples
            destinations: List of (lat, lng) tuples

        Returns:
            Matrix of distances and durations
        """
        if not self.api_key:
            logger.warning("Google Maps API key not configured")
            return self._create_empty_matrix(len(origins), len(destinations))

        # Apply rate limiting
        await self._apply_rate_limit()

        # Build matrix request
        request_body = {
            "origins": [
                {
                    "waypoint": {
                        "location": {"latLng": {"latitude": lat, "longitude": lng}}
                    }
                }
                for lat, lng in origins
            ],
            "destinations": [
                {
                    "waypoint": {
                        "location": {"latLng": {"latitude": lat, "longitude": lng}}
                    }
                }
                for lat, lng in destinations
            ],
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "departureTime": datetime.now().isoformat() + "Z",
            "languageCode": "zh - TW",
            "regionCode": "TW",
            "units": "METRIC",
            "extraComputations": ["TOLLS"],
        }

        # Execute with retry logic
        for attempt in range(self.max_retries):
            try:
                result = await self._execute_api_request(
                    self.matrix_url, request_body, "*"  # Get all fields for matrix
                )

                if result:
                    return self._process_matrix_response(result)

            except Exception as e:
                logger.error(
                    f"Distance matrix calculation failed (attempt {attempt + 1}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(
                        self.retry_delay * (self.backoff_multiplier**attempt)
                    )

        return self._create_empty_matrix(len(origins), len(destinations))

    def _process_matrix_response(self, response: List[Dict]) -> Dict[str, Any]:
        """Process distance matrix response"""
        matrix = {"distances": [], "durations": [], "status": "OK"}

        for row in response:
            distance_row = []
            duration_row = []

            if row.get("error"):
                logger.error(f"Matrix row error: {row['error']}")
                matrix["status"] = "PARTIAL_ERROR"
                continue

            distance_meters = row.get("distanceMeters", 0)
            duration_seconds = self._parse_duration(row.get("duration", "0s")) * 60

            distance_row.append(distance_meters)
            duration_row.append(duration_seconds)

            matrix["distances"].append(distance_row)
            matrix["durations"].append(duration_row)

        return matrix

    def _create_empty_matrix(
        self, num_origins: int, num_destinations: int
    ) -> Dict[str, Any]:
        """Create empty distance matrix as fallback"""
        return {
            "distances": [[0] * num_destinations for _ in range(num_origins)],
            "durations": [[0] * num_destinations for _ in range(num_origins)],
            "status": "NO_API_KEY",
        }

    async def validate_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]:
        """
        Validate and geocode Taiwan addresses

        Args:
            addresses: List of address strings

        Returns:
            List of validated addresses with coordinates
        """
        validated = []

        for address in addresses:
            # For now, return mock validation
            # In production, this would use Google Geocoding API
            validated.append(
                {
                    "original_address": address,
                    "formatted_address": address,
                    "latitude": settings.DEPOT_LAT + (len(validated) * 0.001),
                    "longitude": settings.DEPOT_LNG + (len(validated) * 0.001),
                    "place_id": f"mock_place_{len(validated)}",
                    "confidence": 0.95,
                    "validated": True,
                }
            )

        return validated

    async def get_real_time_traffic(self, route_polyline: str) -> Dict[str, Any]:
        """
        Get real - time traffic conditions for a route

        Args:
            route_polyline: Encoded polyline of the route

        Returns:
            Traffic conditions and delays
        """
        # This would integrate with Google Roads API for traffic
        # For now, return mock data
        return {
            "overall_delay_minutes": 5,
            "traffic_segments": [
                {"severity": "NORMAL", "delay_minutes": 0},
                {"severity": "SLOW", "delay_minutes": 3},
                {"severity": "CONGESTION", "delay_minutes": 2},
            ],
            "updated_at": datetime.now().isoformat(),
        }

    def get_api_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics for monitoring"""
        return {
            "requests_per_second_limit": self.requests_per_second,
            "retry_configuration": {
                "max_retries": self.max_retries,
                "initial_delay": self.retry_delay,
                "backoff_multiplier": self.backoff_multiplier,
            },
            "endpoints": {
                "routes": self.base_url,
                "matrix": self.matrix_url,
                "optimization": self.optimization_url,
            },
        }


# Singleton instance
google_routes_service = GoogleRoutesService()
