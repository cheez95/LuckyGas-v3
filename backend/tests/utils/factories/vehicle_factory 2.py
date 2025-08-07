"""
Vehicle factory for test data generation
"""
from typing import Dict, Any
from datetime import datetime, date, timedelta
import random
from tests.utils.factories.base import BaseFactory
from app.models.vehicle import Vehicle


class VehicleFactory(BaseFactory):
    """Factory for creating Vehicle test data"""
    
    model = Vehicle
    
    async def get_default_data(self) -> Dict[str, Any]:
        """Get default vehicle data"""
        vehicle_types = ["truck", "van", "motorcycle"]
        vehicle_type = random.choice(vehicle_types)
        
        # Set capacity based on vehicle type
        capacity_map = {
            "truck": random.randint(800, 1500),
            "van": random.randint(300, 700),
            "motorcycle": random.randint(50, 150)
        }
        
        return {
            "license_plate": self._generate_license_plate(),
            "type": vehicle_type,
            "capacity_kg": capacity_map[vehicle_type],
            "status": "active",
            "brand": random.choice(["Toyota", "Nissan", "Mitsubishi", "Isuzu", "Ford"]),
            "model": f"Model-{self.random_string(5)}",
            "year": random.randint(2015, 2024),
            "fuel_type": random.choice(["gasoline", "diesel", "hybrid"]),
            "last_maintenance_date": date.today() - timedelta(days=random.randint(1, 90)),
            "next_maintenance_date": date.today() + timedelta(days=random.randint(30, 180)),
            "mileage_km": random.randint(10000, 200000),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    
    def _generate_license_plate(self) -> str:
        """Generate a Taiwan-style license plate"""
        # Taiwan license plate format: ABC-1234 or AB-1234
        letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=random.choice([2, 3])))
        numbers = ''.join(random.choices('0123456789', k=4))
        return f"{letters}-{numbers}"
    
    async def create_fleet(self, count: int = 5) -> list:
        """Create a fleet of vehicles with diverse types"""
        vehicles = []
        vehicle_types = ["truck", "van", "motorcycle"]
        
        for i in range(count):
            vehicle_type = vehicle_types[i % len(vehicle_types)]
            vehicle = await self.create(
                license_plate=f"FLEET-{i:03d}",
                type=vehicle_type
            )
            vehicles.append(vehicle)
        
        return vehicles
    
    async def create_truck(self, **kwargs) -> Vehicle:
        """Create a truck specifically"""
        truck_data = {
            "type": "truck",
            "capacity_kg": random.randint(1000, 1500),
            "fuel_type": "diesel"
        }
        truck_data.update(kwargs)
        return await self.create(**truck_data)
    
    async def create_van(self, **kwargs) -> Vehicle:
        """Create a van specifically"""
        van_data = {
            "type": "van",
            "capacity_kg": random.randint(400, 700),
            "fuel_type": "gasoline"
        }
        van_data.update(kwargs)
        return await self.create(**van_data)
    
    async def create_motorcycle(self, **kwargs) -> Vehicle:
        """Create a motorcycle specifically"""
        motorcycle_data = {
            "type": "motorcycle",
            "capacity_kg": random.randint(50, 100),
            "fuel_type": "gasoline",
            "brand": random.choice(["Yamaha", "Honda", "Suzuki", "SYM", "Kymco"])
        }
        motorcycle_data.update(kwargs)
        return await self.create(**motorcycle_data)
    
    async def create_maintenance_due_vehicle(self, **kwargs) -> Vehicle:
        """Create a vehicle that needs maintenance soon"""
        from datetime import timedelta
        
        maintenance_data = {
            "last_maintenance_date": date.today() - timedelta(days=85),
            "next_maintenance_date": date.today() + timedelta(days=5),
            "mileage_km": random.randint(150000, 200000),
            "status": "active"  # But needs maintenance soon
        }
        maintenance_data.update(kwargs)
        return await self.create(**maintenance_data)
    
    async def create_inactive_vehicle(self, reason: str = "maintenance", **kwargs) -> Vehicle:
        """Create an inactive vehicle"""
        inactive_data = {
            "status": "inactive",
            "inactive_reason": reason,
            "inactive_since": datetime.now() - timedelta(days=random.randint(1, 30))
        }
        inactive_data.update(kwargs)
        return await self.create(**inactive_data)
</content>