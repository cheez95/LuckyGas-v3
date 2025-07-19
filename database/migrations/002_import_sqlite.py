"""
Import data from existing SQLite database to PostgreSQL
"""
import asyncio
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from app.core.database import async_session_maker
from app.models.vehicle import Driver, Vehicle, VehicleType
from app.models.delivery import Delivery, DeliveryPrediction
from sqlalchemy import select


async def import_drivers_and_vehicles():
    """Import drivers and vehicles from SQLite database"""
    sqlite_path = Path(__file__).parent.parent.parent / "raw" / "luckygas.db"
    print(f"Connecting to SQLite database: {sqlite_path}")
    
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    async with async_session_maker() as session:
        # Import drivers
        print("\nImporting drivers...")
        cursor.execute("SELECT * FROM drivers")
        drivers = cursor.fetchall()
        drivers_added = 0
        
        for row in drivers:
            try:
                # Check if driver already exists
                result = await session.execute(
                    select(Driver).where(Driver.employee_id == row['employee_id'])
                )
                if result.scalar_one_or_none():
                    continue
                
                driver = Driver(
                    employee_id=row['employee_id'],
                    name=row['name'],
                    phone=row['phone'],
                    license_number=row['license_type'] or '',
                    license_type=row['license_type'],
                    is_active=bool(row['is_active']) if row['is_active'] is not None else True,
                    is_available=bool(row['is_available']) if row['is_available'] is not None else True,
                    total_deliveries=row['total_deliveries'] or 0,
                    success_rate=row['success_rate'] or 100.0
                )
                
                session.add(driver)
                drivers_added += 1
                
            except Exception as e:
                print(f"Error importing driver {row['name']}: {e}")
                continue
        
        await session.commit()
        print(f"Imported {drivers_added} drivers")
        
        # Import vehicles
        print("\nImporting vehicles...")
        cursor.execute("SELECT * FROM vehicles")
        vehicles = cursor.fetchall()
        vehicles_added = 0
        
        for row in vehicles:
            try:
                # Check if vehicle already exists
                result = await session.execute(
                    select(Vehicle).where(Vehicle.plate_number == row['plate_number'])
                )
                if result.scalar_one_or_none():
                    continue
                
                # Map vehicle type
                vehicle_type = VehicleType.TRUCK
                if row['vehicle_type'] == 'motorcycle':
                    vehicle_type = VehicleType.MOTORCYCLE
                elif row['vehicle_type'] == 'van':
                    vehicle_type = VehicleType.VAN
                
                vehicle = Vehicle(
                    plate_number=row['plate_number'],
                    vehicle_type=vehicle_type,
                    max_cylinders_50kg=row['max_cylinders_50kg'] or 0,
                    max_cylinders_20kg=row['max_cylinders_20kg'] or 0,
                    max_cylinders_16kg=row['max_cylinders_16kg'] or 0,
                    max_cylinders_10kg=row['max_cylinders_10kg'] or 0,
                    max_cylinders_4kg=row['max_cylinders_4kg'] or 0,
                    brand=row['brand'],
                    model=row['model'],
                    year=row['year'],
                    fuel_type=row['fuel_type'],
                    is_active=bool(row['is_active']) if row['is_active'] is not None else True,
                    is_available=bool(row['is_available']) if row['is_available'] is not None else True,
                    total_km=row['total_km'] or 0.0,
                    fuel_efficiency_km_per_liter=row['fuel_efficiency'] if 'fuel_efficiency' in row.keys() else None
                )
                
                # Calculate total capacity
                vehicle.max_cylinders_total = (
                    vehicle.max_cylinders_50kg +
                    vehicle.max_cylinders_20kg +
                    vehicle.max_cylinders_16kg +
                    vehicle.max_cylinders_10kg +
                    vehicle.max_cylinders_4kg
                )
                
                session.add(vehicle)
                vehicles_added += 1
                
            except Exception as e:
                print(f"Error importing vehicle {row['plate_number']}: {e}")
                continue
        
        await session.commit()
        print(f"Imported {vehicles_added} vehicles")
    
    conn.close()


async def import_delivery_history():
    """Import delivery history from Excel"""
    # This would be implemented if we need to process the delivery history Excel file
    # For now, we'll skip this as the Excel file has a different structure
    print("\nDelivery history import from Excel not implemented yet")
    print("The Excel file contains summarized data, not individual delivery records")


if __name__ == "__main__":
    asyncio.run(import_drivers_and_vehicles())