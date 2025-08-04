"""Notification schemas."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

from app.models.notification import NotificationStatus, SMSProvider, NotificationChannel


# SMS Send Schemas
class SMSSendRequest(BaseModel):
    """SMS send request"""

    phone: str = Field(..., description="Recipient phone number")
    message: Optional[str] = Field(
        None, description="Message content (if not using template)"
    )
    message_type: Optional[str] = Field(None, description="Message type for tracking")
    template_code: Optional[str] = Field(None, description="Template code to use")
    template_data: Optional[Dict[str, Any]] = Field(
        None, description="Data for template placeholders"
    )
    provider: Optional[SMSProvider] = Field(
        None, description="Specific provider to use"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        """Basic phone validation"""
        # Remove spaces and hyphens
        cleaned = v.replace(" ", "").replace("-", "")
        # Check if it's a valid Taiwan phone
        if not (
            (cleaned.startswith("09") and len(cleaned) == 10)  # Mobile
            or (cleaned.startswith("0") and len(cleaned) in [9, 10])  # Landline
            or (
                cleaned.startswith("+886") and len(cleaned) in [12, 13]
            )  # International
        ):
            raise ValueError("Invalid Taiwan phone number format")
        return cleaned

    @field_validator("message", mode="after")
    @classmethod
    def validate_message_or_template(cls, v, info):
        """Ensure either message or template is provided"""
        if not v and not info.data.get("template_code"):
            raise ValueError("Either message or template_code must be provided")
        return v


class SMSSendResponse(BaseModel):
    """SMS send response"""

    success: bool
    message_id: Optional[UUID] = None
    provider_message_id: Optional[str] = None
    segments: Optional[int] = None
    cost: Optional[float] = None
    error: Optional[str] = None


class SMSBulkRecipient(BaseModel):
    """Bulk SMS recipient"""

    phone: str
    message: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class SMSBulkSendRequest(BaseModel):
    """Bulk SMS send request"""

    recipients: List[SMSBulkRecipient]
    message_type: str
    default_message: Optional[str] = None
    template_code: Optional[str] = None
    provider: Optional[SMSProvider] = None
    batch_name: Optional[str] = Field(None, description="Name for this batch send")
    batch_size: Optional[int] = Field(
        100, ge=1, le=500, description="Batch size for sending"
    )


class SMSStatusResponse(BaseModel):
    """SMS status response"""

    success: bool
    status: Optional[NotificationStatus] = None
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None


# SMS Template Schemas
class SMSTemplateBase(BaseModel):
    """Base SMS template schema"""

    code: str = Field(..., description="Unique template code")
    name: str = Field(..., description="Template name")
    description: Optional[str] = None
    content: str = Field(..., description="Template content with placeholders")
    language: str = Field("zh-TW", description="Language code")
    variant: str = Field("A", description="Variant for A/B testing")
    weight: int = Field(100, ge=0, le=100, description="Weight for random selection")
    is_active: bool = True


class SMSTemplateCreate(SMSTemplateBase):
    """Create SMS template schema"""

    pass


class SMSTemplateUpdate(BaseModel):
    """Update SMS template schema"""

    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    weight: Optional[int] = Field(None, ge=0, le=100)


class SMSTemplateResponse(SMSTemplateBase):
    """SMS template response"""

    id: UUID
    sent_count: int = 0
    delivered_count: int = 0
    click_count: int = 0
    effectiveness_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Provider Configuration Schemas
class ProviderConfigBase(BaseModel):
    """Base provider configuration schema"""

    provider: SMSProvider
    config: Dict[str, Any] = Field(..., description="Provider-specific configuration")
    is_active: bool = True
    priority: int = Field(0, description="Higher priority = preferred provider")
    rate_limit: Optional[int] = Field(None, description="Messages per minute")
    daily_limit: Optional[int] = Field(None, description="Messages per day")
    cost_per_message: Optional[float] = Field(None, description="Base cost in TWD")
    cost_per_segment: Optional[float] = Field(
        None, description="Additional segment cost"
    )


class ProviderConfigCreate(ProviderConfigBase):
    """Create provider configuration schema"""

    pass


class ProviderConfigUpdate(BaseModel):
    """Update provider configuration schema"""

    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    rate_limit: Optional[int] = None
    daily_limit: Optional[int] = None
    cost_per_message: Optional[float] = None
    cost_per_segment: Optional[float] = None


class ProviderConfigResponse(ProviderConfigBase):
    """Provider configuration response"""

    id: UUID
    total_sent: int = 0
    total_failed: int = 0
    success_rate: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# SMS Log Schemas
class SMSLogResponse(BaseModel):
    """SMS log response"""

    id: UUID
    recipient: str
    sender_id: Optional[str] = None
    message: str
    message_type: Optional[str] = None
    provider: SMSProvider
    provider_message_id: Optional[str] = None
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    cost: Optional[float] = None
    segments: Optional[int] = None
    unicode_message: bool = True
    metadata: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Notification Log Schemas
class NotificationLogResponse(BaseModel):
    """Notification log response"""

    id: UUID
    channel: NotificationChannel
    recipient: str
    notification_type: str
    title: Optional[str] = None
    message: str
    status: NotificationStatus
    user_id: Optional[UUID] = None
    order_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Statistics Schemas
class NotificationStatsResponse(BaseModel):
    """Notification statistics response"""

    start_date: datetime
    end_date: datetime
    sms_stats: Dict[str, Any] = Field(..., description="SMS statistics")
    provider_breakdown: List[Dict[str, Any]] = Field(
        ..., description="Stats by provider"
    )

    model_config = {"from_attributes": True}
