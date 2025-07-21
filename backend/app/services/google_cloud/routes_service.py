"""
Google Routes API Service for route optimization
"""
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
from dataclasses import dataclass
import logging

from app.core.google_cloud_config import get_gcp_config
from app.models.route import Route as DeliveryRoute, RouteStop
from app.models.order import Order
from app.models.customer import Customer
from app.core.config import settings

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
        self.base_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        self.optimization_url = "https://routes.googleapis.com/v1/projects/{}/locations/{}/routeOptimization:optimizeTours"
        self.depot_location = (settings.DEPOT_LAT, settings.DEPOT_LNG)
        
    async def optimize_route(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int = 100,
        time_windows: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Optimize delivery route using Google Routes API
        """
        if not self.api_key:
            logger.warning("Google Maps API key not configured, returning unoptimized route")
            return self._create_unoptimized_route(depot, stops)
        
        try:
            # Build optimization request
            request_body = self._build_optimization_request(
                depot, stops, vehicle_capacity, time_windows
            )
            
            # Make API request
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": "routes.optimizedIntermediateWaypointIndex,routes.duration,routes.distanceMeters,routes.polyline"
                }
                
                async with session.post(
                    self.base_url,
                    json=request_body,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return self._process_route_response(result, stops)
                    else:
                        error_text = await response.text()
                        logger.error(f"Routes API error: {response.status} - {error_text}")
                        return self._create_unoptimized_route(depot, stops)
                        
        except Exception as e:
            logger.error(f"Route optimization failed: {e}")
            return self._create_unoptimized_route(depot, stops)
    
    def _build_optimization_request(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int,
        time_windows: Optional[Dict]
    ) -> Dict:
        """Build request body for Routes API"""
        
        # Create waypoints
        waypoints = []
        
        # Add intermediate waypoints for stops
        for stop in stops:
            waypoint = {
                "location": {
                    "latLng": {
                        "latitude": stop["lat"],
                        "longitude": stop["lng"]
                    }
                },
                "sideOfRoad": True  # Allow stopping on either side
            }
            waypoints.append(waypoint)
        
        request = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": depot[0],
                        "longitude": depot[1]
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": depot[0],
                        "longitude": depot[1]
                    }
                }
            },
            "intermediates": waypoints,
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "optimizeWaypointOrder": True,
            "languageCode": "zh-TW",
            "regionCode": "TW",
            "computeAlternativeRoutes": False,
            "routeModifiers": {
                "avoidTolls": False,
                "avoidHighways": False,
                "avoidFerries": True
            }
        }
        
        return request
    
    def _process_route_response(self, response: Dict, original_stops: List[Dict]) -> Dict:
        """Process the API response and return optimized route"""
        
        if not response.get("routes"):
            return self._create_unoptimized_route(self.depot_location, original_stops)
        
        route = response["routes"][0]
        
        # Get optimized order if available
        optimized_order = []
        if "optimizedIntermediateWaypointIndex" in route:
            optimized_indices = route["optimizedIntermediateWaypointIndex"]
            optimized_order = [original_stops[i] for i in optimized_indices]
        else:
            optimized_order = original_stops
        
        # Add sequence numbers
        for i, stop in enumerate(optimized_order):
            stop["stop_sequence"] = i + 1
            stop["estimated_arrival"] = self._calculate_arrival_time(i, route)
        
        return {
            "stops": optimized_order,
            "total_distance": route.get("distanceMeters", 0),
            "total_duration": route.get("duration", "0s"),
            "polyline": route.get("polyline", {}).get("encodedPolyline", ""),
            "warnings": route.get("warnings", []),
            "optimized": True
        }
    
    def _create_unoptimized_route(self, depot: Tuple[float, float], stops: List[Dict]) -> Dict:
        """Create a basic unoptimized route as fallback"""
        
        # Simple distance-based sorting
        sorted_stops = sorted(stops, key=lambda s: self._calculate_distance(
            depot[0], depot[1], s["lat"], s["lng"]
        ))
        
        for i, stop in enumerate(sorted_stops):
            stop["stop_sequence"] = i + 1
            stop["estimated_arrival"] = datetime.now() + timedelta(minutes=30 * (i + 1))
        
        return {
            "stops": sorted_stops,
            "total_distance": 0,  # Would need to calculate
            "total_duration": "0s",
            "polyline": "",
            "warnings": ["Route optimization unavailable - using distance-based sorting"],
            "optimized": False
        }
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate approximate distance between two points (Haversine formula)"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _calculate_arrival_time(self, stop_index: int, route: Dict) -> datetime:
        """Calculate estimated arrival time for a stop"""
        # This is a simplified calculation
        # In production, you'd parse the route legs for accurate timing
        base_time = datetime.now()
        minutes_per_stop = 30  # Average time including travel and service
        return base_time + timedelta(minutes=minutes_per_stop * (stop_index + 1))
    
    async def optimize_multiple_routes(
        self,
        orders: List[Order],
        drivers: List[Dict],
        date: datetime
    ) -> List[Dict]:
        """
        Optimize routes for multiple drivers
        """
        # Group orders by geographic clusters
        clusters = self._cluster_orders_by_location(orders, len(drivers))
        
        # Optimize each cluster
        optimization_tasks = []
        for i, (driver, cluster) in enumerate(zip(drivers, clusters)):
            task = self._optimize_driver_route(
                driver=driver,
                orders=cluster,
                route_number=f"R{date.strftime('%Y%m%d')}-{i+1:02d}"
            )
            optimization_tasks.append(task)
        
        # Run optimizations in parallel
        optimized_routes = await asyncio.gather(*optimization_tasks)
        
        return optimized_routes
    
    async def _optimize_driver_route(
        self,
        driver: Dict,
        orders: List[Order],
        route_number: str
    ) -> Dict:
        """Optimize a single driver's route"""
        
        # Prepare stops from orders
        stops = []
        for order in orders:
            stop = {
                "order_id": order.id,
                "customer_id": order.customer_id,
                "customer_name": order.customer.short_name if order.customer else f"Customer {order.customer_id}",
                "address": order.delivery_address or order.customer.address,
                "lat": order.customer.latitude or settings.DEPOT_LAT,
                "lng": order.customer.longitude or settings.DEPOT_LNG,
                "priority": order.priority,
                "service_time": self._estimate_service_time(order),
                "products": self._get_order_products(order)
            }
            
            # Add time window if specified
            if hasattr(order.customer, 'delivery_time_start'):
                stop["time_window"] = {
                    "start": order.customer.delivery_time_start,
                    "end": order.customer.delivery_time_end
                }
            
            stops.append(stop)
        
        # Optimize route
        optimized = await self.optimize_route(
            depot=self.depot_location,
            stops=stops,
            vehicle_capacity=driver.get("vehicle_capacity", 100),
            time_windows={
                "start": "08:00",
                "end": "18:00"
            }
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
            "total_distance_km": optimized["total_distance"] / 1000 if optimized["total_distance"] else 0,
            "estimated_duration_minutes": self._parse_duration(optimized["total_duration"]),
            "polyline": optimized.get("polyline", ""),
            "warnings": optimized.get("warnings", []),
            "optimized": optimized.get("optimized", False)
        }
    
    def _cluster_orders_by_location(
        self,
        orders: List[Order],
        n_clusters: int
    ) -> List[List[Order]]:
        """
        Cluster orders by geographic location using k-means
        """
        if len(orders) <= n_clusters:
            # If fewer orders than drivers, assign one per driver
            return [[order] for order in orders] + [[] for _ in range(n_clusters - len(orders))]
        
        try:
            from sklearn.cluster import KMeans
            import numpy as np
            
            # Extract coordinates
            coords = []
            valid_orders = []
            
            for order in orders:
                if order.customer and order.customer.latitude and order.customer.longitude:
                    coords.append([order.customer.latitude, order.customer.longitude])
                    valid_orders.append(order)
            
            if not coords:
                # No valid coordinates, distribute evenly
                orders_per_cluster = len(orders) // n_clusters
                clusters = []
                for i in range(n_clusters):
                    start = i * orders_per_cluster
                    end = start + orders_per_cluster if i < n_clusters - 1 else len(orders)
                    clusters.append(orders[start:end])
                return clusters
            
            coords_array = np.array(coords)
            
            # Perform k-means clustering
            kmeans = KMeans(n_clusters=min(n_clusters, len(valid_orders)), random_state=42)
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
            logger.warning("scikit-learn not available, using simple order distribution")
            orders_per_cluster = len(orders) // n_clusters
            clusters = []
            for i in range(n_clusters):
                start = i * orders_per_cluster
                end = start + orders_per_cluster if i < n_clusters - 1 else len(orders)
                clusters.append(orders[start:end])
            return clusters
    
    def _estimate_service_time(self, order: Order) -> int:
        """Estimate service time for an order in minutes"""
        base_time = 5  # Base time for any delivery
        
        # Add time based on cylinder count
        total_cylinders = 0
        for size in [50, 20, 16, 10, 4]:
            qty_field = f"quantity_{size}kg"
            if hasattr(order, qty_field):
                total_cylinders += getattr(order, qty_field, 0)
        
        # 2 minutes per cylinder
        cylinder_time = total_cylinders * 2
        
        return base_time + cylinder_time
    
    def _get_order_products(self, order: Order) -> Dict[str, int]:
        """Get product quantities from order"""
        products = {}
        
        for size in [50, 20, 16, 10, 4]:
            qty_field = f"quantity_{size}kg"
            if hasattr(order, qty_field):
                qty = getattr(order, qty_field, 0)
                if qty > 0:
                    products[f"{size}kg"] = qty
        
        return products
    
    def _determine_area(self, stops: List[Dict]) -> str:
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
            seconds = int(duration_str.rstrip('s'))
            return seconds // 60
        except:
            return 0


# Singleton instance
google_routes_service = GoogleRoutesService()