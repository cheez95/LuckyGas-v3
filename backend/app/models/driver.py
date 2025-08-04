"""
Driver model for route assignments
"""

from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Driver(Base):
    """
    Driver model representing delivery personnel
    """

    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)
    license_number = Column(String, nullable=False, unique=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)

    # Performance metrics
    total_deliveries = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="driver_profile")
    vehicle = relationship("Vehicle", back_populates="driver")
    routes = relationship("Route", back_populates="driver")

    def __repr__(self):
        return f"<Driver {self.name} ({self.phone})>"
