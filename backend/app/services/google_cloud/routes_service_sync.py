"""
Synchronous Google Routes API Service for route optimization
Simplified version for Lucky Gas system using SQLite (sync database)
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import requests
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
    products: Dict[str, int] = field(default_factory=dict)


class GoogleRoutesServiceSync:
    """
    Synchronous service for route optimization using Google Routes API
    Designed for use with sync database operations (SQLite)
    """

    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY if hasattr(settings, 'GOOGLE_MAPS_API_KEY') else None
        self.base_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        self.matrix_url = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
        
        # Depot location (Taipei area for testing)
        self.depot_location = (
            getattr(settings, 'DEPOT_LAT', 25.0330),
            getattr(settings, 'DEPOT_LNG', 121.5654)
        )
        
        # Rate limiting
        self.requests_per_second = 10
        self.last_request_time = 0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0

    def optimize_route(
        self,
        depot: Tuple[float, float],
        stops: List[Dict],
        vehicle_capacity: int = 100,
        time_windows: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Optimize delivery route using Google Routes API
        Falls back to simple optimization if API is unavailable
        """
        if not self.api_key:
            logger.warning(
                "Google Maps API key not configured, using fallback optimization"
            )
            return self._create_fallback_route(depot, stops)
        
        try:
            # Rate limiting
            self._apply_rate_limit()
            
            # For now, use the fallback algorithm
            # Google Routes API integration would require proper project setup
            logger.info("Using fallback optimization algorithm")
            return self._create_fallback_route(depot, stops)
            
        except Exception as e:
            logger.error(f"Error during route optimization: {e}")
            return self._create_fallback_route(depot, stops)

    def _apply_rate_limit(self):
        """Apply rate limiting to API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        
        self.last_request_time = time.time()

    def _create_fallback_route(
        self, 
        depot: Tuple[float, float], 
        stops: List[Dict]
    ) -> Dict[str, Any]:
        """
        Create a simple optimized route using nearest neighbor algorithm
        This is a fallback when Google API is unavailable
        """
        from math import sqrt
        
        optimized_stops = []
        remaining_stops = stops.copy()
        current_location = depot
        total_distance = 0
        
        while remaining_stops:
            # Find nearest stop
            nearest_stop = None
            min_distance = float('inf')
            
            for stop in remaining_stops:
                # Calculate Euclidean distance (simplified)
                distance = sqrt(
                    (stop["lat"] - current_location[0]) ** 2 +
                    (stop["lng"] - current_location[1]) ** 2
                )
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_stop = stop
            
            if nearest_stop:
                # Add to optimized route
                nearest_stop["stop_sequence"] = len(optimized_stops) + 1
                nearest_stop["distance_from_previous"] = min_distance * 111000  # Convert to meters (approx)
                nearest_stop["estimated_arrival"] = (
                    datetime.now() + timedelta(minutes=30 * len(optimized_stops))
                ).isoformat()
                
                optimized_stops.append(nearest_stop)
                remaining_stops.remove(nearest_stop)
                current_location = (nearest_stop["lat"], nearest_stop["lng"])
                total_distance += nearest_stop["distance_from_previous"]
        
        # Calculate total duration (estimate 30 min per stop)
        total_duration_minutes = len(optimized_stops) * 30
        
        return {
            "stops": optimized_stops,
            "total_distance": int(total_distance),
            "total_duration": f"{total_duration_minutes * 60}s",
            "total_duration_minutes": total_duration_minutes,
            "polyline": "",  # Would be populated by Google API
            "warnings": ["Using fallback optimization algorithm"],
            "optimized": False,
            "optimization_savings": {
                "distance_saved_meters": 0,
                "time_saved_minutes": 0,
                "fuel_saved_liters": 0
            }
        }

    def calculate_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]]
    ) -> Dict[str, Any]:
        """
        Calculate distance matrix between origins and destinations
        Falls back to Euclidean distance if API unavailable
        """
        from math import sqrt
        
        matrix = []
        
        for origin in origins:
            row = []
            for destination in destinations:
                # Calculate Euclidean distance
                distance = sqrt(
                    (destination[0] - origin[0]) ** 2 +
                    (destination[1] - origin[1]) ** 2
                ) * 111000  # Convert to meters (approximation)
                
                row.append({
                    "distance_meters": int(distance),
                    "duration_seconds": int(distance / 10)  # Assume 10m/s average speed
                })
            matrix.append(row)
        
        return {
            "matrix": matrix,
            "method": "euclidean_fallback"
        }

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to coordinates
        Returns None if geocoding fails
        """
        if not self.api_key:
            logger.warning("Google Maps API key not configured for geocoding")
            return None
        
        try:
            # Rate limiting
            self._apply_rate_limit()
            
            # Google Geocoding API endpoint
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": address,
                "key": self.api_key,
                "region": "tw",  # Taiwan region hint
                "language": "zh-TW"
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data["status"] == "OK" and data["results"]:
                    location = data["results"][0]["geometry"]["location"]
                    return (location["lat"], location["lng"])
            
            logger.warning(f"Geocoding failed for address: {address}")
            return None
            
        except Exception as e:
            logger.error(f"Error geocoding address {address}: {e}")
            return None

    def validate_route(self, route: Dict[str, Any]) -> bool:
        """
        Validate an optimized route
        """
        if not route:
            return False
        
        if "stops" not in route or not route["stops"]:
            return False
        
        # Check that all stops have required fields
        required_fields = ["stop_sequence", "lat", "lng"]
        for stop in route["stops"]:
            if not all(field in stop for field in required_fields):
                return False
        
        return True


# Singleton instance for reuse
_routes_service_sync = None

def get_routes_service_sync() -> GoogleRoutesServiceSync:
    """Get or create singleton instance of sync routes service"""
    global _routes_service_sync
    if _routes_service_sync is None:
        _routes_service_sync = GoogleRoutesServiceSync()
    return _routes_service_sync