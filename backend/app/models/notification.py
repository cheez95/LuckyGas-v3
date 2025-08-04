"""Notification and SMS log models."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    Float,
    JSON,
    Enum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class NotificationStatus(str, enum.Enum):
    """Notification delivery status"""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SMSProvider(str, enum.Enum):
    """Supported SMS providers"""

    TWILIO = "twilio"
    CHUNGHWA = "chunghwa"  # 中華電信
    EVERY8D = "every8d"
    MITAKE = "mitake"


class NotificationChannel(str, enum.Enum):
    """Notification channels"""

    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class SMSLog(Base):
    """SMS delivery log for audit trail"""

    __tablename__ = "sms_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Message details
    recipient = Column(String(50), nullable=False, index=True)
    sender_id = Column(String(50))
    message = Column(Text, nullable=False)
    message_type = Column(String(50))  # order_confirmation, delivery_notification, etc.

    # Provider details
    provider = Column(Enum(SMSProvider), nullable=False)
    provider_message_id = Column(String(255))  # Provider's tracking ID

    # Status tracking
    status = Column(
        Enum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    # Metadata
    cost = Column(Float)  # Cost in TWD
    segments = Column(Integer, default=1)  # Number of SMS segments
    unicode_message = Column(Boolean, default=True)  # Unicode support for Chinese

    # Additional data
    notification_metadata = Column(JSON)  # Store order_id, customer_id, etc.
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Indexes for better query performance
    __table_args__ = (
        Index("idx_sms_logs_created_at", "created_at"),
        Index("idx_sms_logs_status_created", "status", "created_at"),
        Index("idx_sms_logs_provider_status", "provider", "status"),
    )


class SMSTemplate(Base):
    """SMS message templates"""

    __tablename__ = "sms_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template identification
    code = Column(
        String(50), unique=True, nullable=False, index=True
    )  # order_confirmation, etc.
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Template content
    content = Column(Text, nullable=False)  # Template with placeholders like {order_id}

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    language = Column(String(10), default="zh-TW", nullable=False)

    # A/B testing
    variant = Column(String(10), default="A")  # A, B, C for testing
    weight = Column(Integer, default=100)  # Weight for random selection (0-100)

    # Performance metrics
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)  # If contains links
    effectiveness_score = Column(Float)  # Calculated effectiveness

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Indexes
    __table_args__ = (
        Index("idx_sms_templates_code_active", "code", "is_active"),
        Index("idx_sms_templates_code_variant", "code", "variant"),
    )


class NotificationLog(Base):
    """General notification log for all channels"""

    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Notification details
    channel = Column(Enum(NotificationChannel), nullable=False, index=True)
    recipient = Column(String(255), nullable=False, index=True)  # Phone, email, user_id
    notification_type = Column(String(50), nullable=False)

    # Content
    title = Column(String(255))
    message = Column(Text, nullable=False)

    # Status
    status = Column(
        Enum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Related IDs
    user_id = Column(UUID(as_uuid=True), index=True)
    order_id = Column(UUID(as_uuid=True), index=True)

    # Metadata
    notification_metadata = Column(JSON)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))

    # Indexes
    __table_args__ = (
        Index("idx_notification_logs_user_created", "user_id", "created_at"),
        Index("idx_notification_logs_channel_status", "channel", "status"),
    )


class ProviderConfig(Base):
    """SMS provider configuration"""

    __tablename__ = "provider_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Provider identification
    provider = Column(Enum(SMSProvider), unique=True, nullable=False)

    # Configuration (encrypted in production)
    config = Column(JSON, nullable=False)  # API keys, URLs, etc.

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0)  # Higher = preferred

    # Rate limiting
    rate_limit = Column(Integer)  # Messages per minute
    daily_limit = Column(Integer)  # Messages per day

    # Cost tracking
    cost_per_message = Column(Float)  # Base cost in TWD
    cost_per_segment = Column(Float)  # Additional segment cost

    # Statistics
    total_sent = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    success_rate = Column(Float)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
