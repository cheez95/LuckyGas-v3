"""
Vehicle model for dispatch operations
"""

import enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class VehicleType(str, enum.Enum):
    """Vehicle types"""

    TRUCK_SMALL = "truck_small"  # 小貨車
    TRUCK_MEDIUM = "truck_medium"  # 中型貨車
    TRUCK_LARGE = "truck_large"  # 大貨車
    VAN = "van"  # 廂型車
    MOTORCYCLE = "motorcycle"  # 機車


class VehicleStatus(str, enum.Enum):
    """Vehicle status"""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class Vehicle(Base):
    """Vehicle information for delivery operations"""

    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)

    # Vehicle identification
    vehicle_number = Column(String(50), unique=True, nullable=False)  # 車號
    license_plate = Column(String(20), unique=True, nullable=False)  # 車牌

    # Vehicle details
    vehicle_type = Column(SQLEnum(VehicleType), nullable=False)
    brand = Column(String(50), nullable=True)
    model = Column(String(50), nullable=True)
    year = Column(Integer, nullable=True)
    color = Column(String(30), nullable=True)

    # Capacity
    max_weight_kg = Column(Float, default=1000.0)
    max_cylinders_50kg = Column(Integer, default=20)
    max_cylinders_20kg = Column(Integer, default=50)
    max_cylinders_16kg = Column(Integer, default=60)
    max_cylinders_10kg = Column(Integer, default=100)
    max_cylinders_4kg = Column(Integer, default=200)

    # Status and assignment
    status = Column(SQLEnum(VehicleStatus), default=VehicleStatus.ACTIVE)
    assigned_driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_available = Column(Boolean, default=True)

    # Maintenance tracking
    last_maintenance_date = Column(DateTime, nullable=True)
    next_maintenance_date = Column(DateTime, nullable=True)
    maintenance_notes = Column(String(500), nullable=True)

    # GPS tracking
    has_gps = Column(Boolean, default=True)
    gps_device_id = Column(String(100), nullable=True)

    # Additional specs
    fuel_type = Column(String(20), nullable=True)  # 汽油, 柴油
    fuel_efficiency_km_per_liter = Column(Float, nullable=True)

    # Insurance and registration
    insurance_expiry = Column(DateTime, nullable=True)
    registration_expiry = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    assigned_driver = relationship("User", back_populates="assigned_vehicle")
    driver = relationship("Driver", back_populates="vehicle")

    def __repr__(self):
        return f"<Vehicle {self.vehicle_number} - {self.license_plate}>"
