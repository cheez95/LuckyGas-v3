"""
Audit log model for tracking all system actions.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"

    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Payments
    PAYMENT_CREATED = "payment_created"
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"

    # Webhooks
    WEBHOOK_RECEIVED = "webhook_received"
    WEBHOOK_PROCESSED = "webhook_processed"
    WEBHOOK_FAILED = "webhook_failed"

    # API
    API_CALL = "api_call"
    API_ERROR = "api_error"

    # Security
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    SECURITY_ALERT = "security_alert"

    # System
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    BACKUP_CREATED = "backup_created"
    MAINTENANCE_MODE = "maintenance_mode"


class AuditLog(Base):
    """Model for audit logging."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Who performed the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user = relationship("User", back_populates="audit_logs")
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # What action was performed
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type = Column(
        String(50), nullable=True, index=True
    )  # order, customer, payment, etc.
    resource_id = Column(String(255), nullable=True)  # ID of the affected resource

    # Additional details
    details = Column(JSONB, nullable=True)  # JSON with action-specific details
    old_values = Column(JSONB, nullable=True)  # For update operations
    new_values = Column(JSONB, nullable=True)  # For update operations

    # When it happened
    performed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Result
    success = Column(String(10), default="true")  # "true", "false", "partial"
    error_message = Column(Text, nullable=True)

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_date_action", "performed_at", "action"),
    )
