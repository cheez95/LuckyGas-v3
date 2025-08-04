"""Vehicle service for managing delivery vehicles."""

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class VehicleService:
    """Service for vehicle operations."""

    async def get_vehicles_by_ids(
        self, vehicle_ids: List[int], session: Optional[AsyncSession] = None
    ) -> List[dict]:
        """Get vehicles by IDs."""
        # For now, return mock data for testing
        vehicles = []
        for vid in vehicle_ids:
            vehicles.append(
                {
                    "id": vid,
                    "driver_id": 200 + vid,
                    "driver_name": f"Driver {vid}",
                    "capacity": {"16kg": 20, "20kg": 16, "50kg": 8},
                    "depot_lat": 25.0350,
                    "depot_lng": 121.5650,
                    "is_available": True,
                }
            )
        return vehicles


# Singleton instance
vehicle_service = VehicleService()
