"""
Google Routes API integration service for route optimization
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from app.core.cache import cache
from app.core.google_cloud_config import get_gcp_config

logger = logging.getLogger(__name__)


class TravelMode(str, Enum):
    DRIVE = "DRIVE"
    WALK = "WALK"
    BICYCLE = "BICYCLE"
    TRANSIT = "TRANSIT"


class RoutingPreference(str, Enum):
    TRAFFIC_AWARE = "TRAFFIC_AWARE"
    TRAFFIC_AWARE_OPTIMAL = "TRAFFIC_AWARE_OPTIMAL"
    TRAFFIC_UNAWARE = "TRAFFIC_UNAWARE"


@dataclass
class Location:
    """Represents a geographic location"""

    latitude: float
    longitude: float
    address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location": {
                "latLng": {"latitude": self.latitude, "longitude": self.longitude}
            }
        }


@dataclass
class RouteStop:
    """Represents a stop in a route"""

    location: Location
    order_id: str
    delivery_time_window: Optional[Tuple[datetime, datetime]] = None
    service_duration_minutes: int = 10  # Default 10 minutes per stop
    priority: int = 1  # 1 - 5, higher is more important
    notes: Optional[str] = None


@dataclass
class RouteRequest:
    """Request parameters for route optimization"""

    origin: Location
    destination: Location
    waypoints: List[RouteStop]
    departure_time: Optional[datetime] = None
    travel_mode: TravelMode = TravelMode.DRIVE
    routing_preference: RoutingPreference = RoutingPreference.TRAFFIC_AWARE_OPTIMAL
    avoid_highways: bool = False
    avoid_tolls: bool = True  # Default avoid tolls in Taiwan
    optimize_waypoint_order: bool = True


@dataclass
class RouteResult:
    """Result from route optimization"""

    total_distance_meters: int
    total_duration_seconds: int
    optimized_waypoint_order: List[int]
    polyline: str
    legs: List[Dict[str, Any]]
    warnings: List[str]
    bounds: Dict[str, Any]


class GoogleRoutesService:
    """Service for interacting with Google Routes API"""

    BASE_URL = "https://routes.googleapis.com / directions / v2:computeRoutes"
    MATRIX_URL = (
        "https://routes.googleapis.com / distanceMatrix / v2:computeRouteMatrix"
    )

    def __init__(self):
        self.config = None
        self._api_key = None
        self.session = None

    async def initialize(self):
        """Initialize the service with configuration"""
        if not self.config:
            self.config = get_gcp_config()
            self._api_key = await self.config.get_maps_api_key()

        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()

    async def optimize_route(self, request: RouteRequest) -> RouteResult:
        """
        Optimize a route with multiple stops

        Args:
            request: RouteRequest with origin, destination, and waypoints

        Returns:
            RouteResult with optimized route information
        """
        await self.initialize()

        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"Route found in cache: {cache_key}")
            return RouteResult(**json.loads(cached_result))

        # Build request payload
        payload = self._build_route_request(request)

        # Add field mask to specify what we want in response
        headers = {
            "Content - Type": "application / json",
            "X - Goog - Api - Key": self._api_key,
            "X - Goog - FieldMask": "routes.duration, routes.distanceMeters, routes.polyline.encodedPolyline, routes.legs, routes.optimizedIntermediateWaypointIndex, routes.warnings, routes.viewport",
        }

        try:
            async with self.session.post(
                self.BASE_URL, json=payload, headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Routes API error: {response.status} - {error_text}")
                    raise Exception(f"Routes API error: {response.status}")

                data = await response.json()

                if not data.get("routes"):
                    raise Exception("No routes found")

                route = data["routes"][0]
                result = self._parse_route_response(route, request)

                # Cache the result for 1 hour
                await cache.set(cache_key, json.dumps(result.__dict__), expire=3600)

                return result

        except Exception as e:
            logger.error(f"Error optimizing route: {e}")
            raise

    async def calculate_distance_matrix(
        self, origins: List[Location], destinations: List[Location]
    ) -> Dict[str, Any]:
        """
        Calculate distance matrix between multiple origins and destinations

        Args:
            origins: List of origin locations
            destinations: List of destination locations

        Returns:
            Distance matrix with distances and durations
        """
        await self.initialize()

        payload = {
            "origins": [origin.to_dict() for origin in origins],
            "destinations": [dest.to_dict() for dest in destinations],
            "travelMode": TravelMode.DRIVE.value,
            "routingPreference": RoutingPreference.TRAFFIC_AWARE.value,
        }

        headers = {
            "Content - Type": "application / json",
            "X - Goog - Api - Key": self._api_key,
            "X - Goog - FieldMask": "originIndex, destinationIndex, distanceMeters, duration, status",
        }

        try:
            async with self.session.post(
                self.MATRIX_URL, json=payload, headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"Distance Matrix API error: {response.status} - {error_text}"
                    )
                    raise Exception(f"Distance Matrix API error: {response.status}")

                # The response is a stream of JSON objects
                matrix = []
                async for line in response.content:
                    if line.strip():
                        matrix.append(json.loads(line))

                return self._parse_distance_matrix(
                    matrix, len(origins), len(destinations)
                )

        except Exception as e:
            logger.error(f"Error calculating distance matrix: {e}")
            raise

    def _build_route_request(self, request: RouteRequest) -> Dict[str, Any]:
        """Build the API request payload"""
        payload = {
            "origin": request.origin.to_dict(),
            "destination": request.destination.to_dict(),
            "travelMode": request.travel_mode.value,
            "routingPreference": request.routing_preference.value,
            "computeAlternativeRoutes": False,
            "routeModifiers": {
                "avoidTolls": request.avoid_tolls,
                "avoidHighways": request.avoid_highways,
                "avoidFerries": True,
            },
            "languageCode": "zh - TW",
            "units": "METRIC",
        }

        # Add waypoints
        if request.waypoints:
            waypoints = []
            for stop in request.waypoints:
                waypoint = stop.location.to_dict()
                waypoint["via"] = False  # Don't force route through waypoint
                waypoints.append(waypoint)

            payload["intermediates"] = waypoints

            # Request waypoint optimization
            if request.optimize_waypoint_order:
                payload["optimizeWaypointOrder"] = True

        # Add departure time if specified
        if request.departure_time:
            payload["departureTime"] = request.departure_time.isoformat() + "Z"

        return payload

    def _parse_route_response(
        self, route: Dict[str, Any], request: RouteRequest
    ) -> RouteResult:
        """Parse the API response into RouteResult"""
        # Get optimized waypoint order
        optimized_order = []
        if "optimizedIntermediateWaypointIndex" in route:
            optimized_order = route["optimizedIntermediateWaypointIndex"]
        else:
            # No optimization, use original order
            optimized_order = list(range(len(request.waypoints)))

        return RouteResult(
            total_distance_meters=route.get("distanceMeters", 0),
            total_duration_seconds=route.get("duration", "0s").rstrip("s"),
            optimized_waypoint_order=optimized_order,
            polyline=route.get("polyline", {}).get("encodedPolyline", ""),
            legs=route.get("legs", []),
            warnings=route.get("warnings", []),
            bounds=route.get("viewport", {}),
        )

    def _parse_distance_matrix(
        self, matrix_data: List[Dict[str, Any]], num_origins: int, num_destinations: int
    ) -> Dict[str, Any]:
        """Parse distance matrix response into structured format"""
        matrix = [[None for _ in range(num_destinations)] for _ in range(num_origins)]

        for element in matrix_data:
            if element.get("status") == "OK":
                origin_idx = element.get("originIndex", 0)
                dest_idx = element.get("destinationIndex", 0)

                matrix[origin_idx][dest_idx] = {
                    "distance_meters": element.get("distanceMeters", 0),
                    "duration_seconds": int(element.get("duration", "0s").rstrip("s")),
                }

        return {
            "matrix": matrix,
            "origins": num_origins,
            "destinations": num_destinations,
        }

    def _generate_cache_key(self, request: RouteRequest) -> str:
        """Generate a cache key for the route request"""
        # Create a unique key based on locations and parameters
        key_parts = [
            f"{request.origin.latitude}, {request.origin.longitude}",
            f"{request.destination.latitude}, {request.destination.longitude}",
            request.travel_mode.value,
            request.routing_preference.value,
            str(request.optimize_waypoint_order),
        ]

        # Add waypoints
        for stop in request.waypoints:
            key_parts.append(f"{stop.location.latitude}, {stop.location.longitude}")

        return f"route:{':'.join(key_parts)}"


# Singleton instance
_routes_service = None


async def get_routes_service() -> GoogleRoutesService:
    """Get or create the routes service instance"""
    global _routes_service
    if _routes_service is None:
        _routes_service = GoogleRoutesService()
        await _routes_service.initialize()
    return _routes_service
