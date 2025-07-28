"""
Webhook log model for tracking and auditing webhook events.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from app.core.database import Base


class WebhookStatus(str, enum.Enum):
    """Webhook processing status."""
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class WebhookLog(Base):
    """Model for logging webhook events."""
    
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)  # stripe, ecpay, twilio, etc.
    event_id = Column(String(255), nullable=False)  # Provider's event ID
    event_type = Column(String(100), nullable=False)  # payment.success, sms.delivered, etc.
    payload = Column(JSONB, nullable=False)  # Full webhook payload
    status = Column(Enum(WebhookStatus), default=WebhookStatus.RECEIVED, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(255), nullable=True)
    signature_valid = Column(String(10), nullable=True)  # "valid", "invalid", "unchecked"
    
    # Response
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    
    # Processing metadata
    processing_time_ms = Column(Integer, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_webhook_provider_event', 'provider', 'event_id'),
        Index('idx_webhook_status_received', 'status', 'received_at'),
        Index('idx_webhook_type_date', 'event_type', 'received_at'),
    )