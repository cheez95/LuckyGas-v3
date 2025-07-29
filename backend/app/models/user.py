from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from app.core.database import Base


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    MANAGER = "manager"
    OFFICE_STAFF = "office_staff"
    DRIVER = "driver"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.OFFICE_STAFF)
    
    # Security fields
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String, nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    assigned_routes = relationship("RoutePlan", foreign_keys="RoutePlan.driver_id", back_populates="driver")
    assigned_vehicle = relationship("Vehicle", foreign_keys="Vehicle.assigned_driver_id", back_populates="assigned_driver", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")