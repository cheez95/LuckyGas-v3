from enum import Enum

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    MANAGER = "MANAGER"
    OFFICE_STAFF = "OFFICE_STAFF"
    DRIVER = "DRIVER"
    CUSTOMER = "CUSTOMER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.OFFICE_STAFF)

    # Security fields - commented out until database migration
    # two_factor_enabled = Column(Boolean, default=False)
    # two_factor_secret = Column(String, nullable=True)
    # last_login = Column(DateTime(timezone=True), nullable=True)
    # password_changed_at = Column(DateTime(timezone=True), nullable=True)
    # failed_login_attempts = Column(Integer, default=0)
    # locked_until = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    assigned_routes = relationship(
        "RoutePlan", foreign_keys="RoutePlan.driver_id", back_populates="driver"
    )
    assigned_vehicle = relationship(
        "Vehicle",
        foreign_keys="Vehicle.assigned_driver_id",
        back_populates="assigned_driver",
        uselist=False,
    )
    driver_profile = relationship("Driver", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")
