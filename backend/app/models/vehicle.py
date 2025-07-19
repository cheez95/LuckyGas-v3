from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from app.core.database import Base


class VehicleType(str, Enum):
    TRUCK = "truck"
    VAN = "van"
    MOTORCYCLE = "motorcycle"


class Driver(Base):
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Personal info
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    license_number = Column(String(50), nullable=False)
    license_type = Column(String(50))  # 職業大貨車, 普通小型車, etc.
    
    # Status
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    
    # Location tracking
    last_known_latitude = Column(Float)
    last_known_longitude = Column(Float)
    last_location_update = Column(DateTime(timezone=True))
    
    # Performance
    total_deliveries = Column(Integer, default=0)
    success_rate = Column(Float, default=100.0)
    avg_delivery_time_minutes = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(20), unique=True, index=True, nullable=False)
    vehicle_type = Column(SQLEnum(VehicleType), nullable=False)
    
    # Capacity (total cylinders)
    max_cylinders_50kg = Column(Integer, default=0)
    max_cylinders_20kg = Column(Integer, default=0)
    max_cylinders_16kg = Column(Integer, default=0)
    max_cylinders_10kg = Column(Integer, default=0)
    max_cylinders_4kg = Column(Integer, default=0)
    max_cylinders_total = Column(Integer, default=0)
    
    # Vehicle info
    brand = Column(String(50))
    model = Column(String(50))
    year = Column(Integer)
    fuel_type = Column(String(20))  # gasoline, diesel, electric
    
    # Status
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    
    # Maintenance
    last_maintenance_date = Column(DateTime(timezone=True))
    next_maintenance_date = Column(DateTime(timezone=True))
    maintenance_notes = Column(String(500))
    
    # Performance
    total_km = Column(Float, default=0.0)
    fuel_efficiency_km_per_liter = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())