"""
GPS tracking service for driver location management
"""

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DriverLocation:
    """Driver location data"""

    driver_id: int
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class GPSService:
    """Service for managing driver GPS locations"""

    def __init__(self):
        # In - memory storage for driver locations
        # In production, this would use Redis or similar
        self._driver_locations: Dict[int, DriverLocation] = {}
        self._location_history: Dict[int, List[DriverLocation]] = defaultdict(list)
        self._max_history_size = 100  # Keep last 100 positions per driver

    async def update_driver_location(
        self,
        driver_id: int,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> DriverLocation:
        """Update driver's current location"""
        location = DriverLocation(
            driver_id=driver_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed,
            heading=heading,
            timestamp=timestamp or datetime.utcnow(),
        )

        # Store current location
        self._driver_locations[driver_id] = location

        # Add to history
        history = self._location_history[driver_id]
        history.append(location)

        # Trim history if too large
        if len(history) > self._max_history_size:
            self._location_history[driver_id] = history[-self._max_history_size :]

        logger.info(
            f"Updated location for driver {driver_id}: "
            f"({latitude}, {longitude}) at {location.timestamp}"
        )

        return location

    async def get_driver_location(self, driver_id: int) -> Optional[DriverLocation]:
        """Get driver's current location"""
        return self._driver_locations.get(driver_id)

    async def get_all_driver_locations(self) -> Dict[int, DriverLocation]:
        """Get all drivers' current locations"""
        # Filter out stale locations (older than 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        active_locations = {
            driver_id: location
            for driver_id, location in self._driver_locations.items()
            if location.timestamp > cutoff_time
        }
        return active_locations

    async def get_driver_location_history(
        self, driver_id: int, minutes: int = 60
    ) -> List[DriverLocation]:
        """Get driver's location history for the past N minutes"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        history = self._location_history.get(driver_id, [])

        # Filter by time
        recent_history = [loc for loc in history if loc.timestamp > cutoff_time]

        return recent_history

    async def calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    async def estimate_arrival_time(
        self, driver_id: int, destination_lat: float, destination_lon: float
    ) -> Optional[datetime]:
        """Estimate arrival time based on current location and speed"""
        location = await self.get_driver_location(driver_id)
        if not location:
            return None

        # Calculate distance
        distance = await self.calculate_distance(
            location.latitude, location.longitude, destination_lat, destination_lon
        )

        # Estimate speed (use current speed or default)
        speed_kmh = (
            location.speed if location.speed else 30
        )  # Default 30 km / h in city

        # Calculate time (hours)
        time_hours = distance / speed_kmh
        time_minutes = time_hours * 60

        # Return estimated arrival time
        return datetime.utcnow() + timedelta(minutes=time_minutes)

    async def is_driver_near_location(
        self,
        driver_id: int,
        target_lat: float,
        target_lon: float,
        radius_meters: float = 100,
    ) -> bool:
        """Check if driver is within radius of target location"""
        location = await self.get_driver_location(driver_id)
        if not location:
            return False

        # Calculate distance
        distance_km = await self.calculate_distance(
            location.latitude, location.longitude, target_lat, target_lon
        )

        # Convert to meters and check
        distance_meters = distance_km * 1000
        return distance_meters <= radius_meters

    async def get_drivers_nearby(
        self, latitude: float, longitude: float, radius_km: float = 5.0
    ) -> List[Tuple[int, float]]:
        """
        Get all drivers within radius of a location
        Returns list of (driver_id, distance_km) tuples
        """
        nearby_drivers = []

        for driver_id, location in self._driver_locations.items():
            # Skip stale locations
            if datetime.utcnow() - location.timestamp > timedelta(minutes=5):
                continue

            # Calculate distance
            distance = await self.calculate_distance(
                latitude, longitude, location.latitude, location.longitude
            )

            if distance <= radius_km:
                nearby_drivers.append((driver_id, distance))

        # Sort by distance
        nearby_drivers.sort(key=lambda x: x[1])

        return nearby_drivers

    async def clear_driver_location(self, driver_id: int):
        """Clear driver's location (e.g., when they go offline)"""
        if driver_id in self._driver_locations:
            del self._driver_locations[driver_id]
        if driver_id in self._location_history:
            del self._location_history[driver_id]

        logger.info(f"Cleared location data for driver {driver_id}")


# Global GPS service instance
gps_service = GPSService()
