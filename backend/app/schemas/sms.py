"""SMS - related Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.models.notification import NotificationStatus, SMSProvider


class SMSSendRequest(BaseModel):
    """Request model for sending SMS"""

    phone: str = Field(..., description="Recipient phone number")
    message: Optional[str] = Field(None, description="Direct message content")
    message_type: Optional[str] = Field(None, description="Message type for tracking")
    template_code: Optional[str] = Field(None, description="Template code to use")
    template_data: Optional[Dict[str, Any]] = Field(
        None, description="Template variables"
    )
    provider: Optional[SMSProvider] = Field(
        None, description="Specific provider to use"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator("phone")
    def validate_phone(cls, v):
        # Remove non - numeric characters
        cleaned = "".join(filter(str.isdigit, v))

        # Validate Taiwan phone format
        if cleaned.startswith("886"):
            if len(cleaned) != 12:  # 886 + 9 digits
                raise ValueError("Invalid Taiwan phone number format")
        elif cleaned.startswith("09"):
            if len(cleaned) != 10:
                raise ValueError("Invalid Taiwan mobile number format")
        else:
            raise ValueError("Phone number must start with 09 or 886")

        return v

    @validator("message")
    def validate_message_or_template(cls, v, values):
        if not v and not values.get("template_code"):
            raise ValueError("Either message or template_code must be provided")
        return v


class SMSResendRequest(BaseModel):
    """Request model for resending SMS"""

    message_id: UUID = Field(..., description="Original message ID to resend")


class SMSLogResponse(BaseModel):
    """Response model for SMS log"""

    id: UUID
    recipient: str
    message: str
    message_type: Optional[str]
    provider: SMSProvider
    status: NotificationStatus
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    failed_at: Optional[datetime]
    error_message: Optional[str]
    cost: float
    segments: int
    created_at: datetime

    class Config:
        orm_mode = True


class SMSStatsResponse(BaseModel):
    """Response model for SMS statistics"""

    total_sent: int
    total_delivered: int
    total_failed: int
    total_pending: int
    total_cost: float
    success_rate: float
    provider_stats: Dict[str, Dict[str, Any]]


class SMSTemplateBase(BaseModel):
    """Base model for SMS template"""

    code: str = Field(..., description="Template code identifier")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    content: str = Field(..., description="Template content with placeholders")
    language: str = Field("zh - TW", description="Template language")
    variant: str = Field("A", description="A / B test variant")
    weight: int = Field(
        100, ge=0, le=100, description="Selection weight for A / B testing"
    )


class SMSTemplateCreate(SMSTemplateBase):
    """Create model for SMS template"""

    is_active: bool = Field(True, description="Whether template is active")


class SMSTemplateUpdate(BaseModel):
    """Update model for SMS template"""

    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    weight: Optional[int] = Field(None, ge=0, le=100)


class SMSTemplateResponse(SMSTemplateBase):
    """Response model for SMS template"""

    id: UUID
    is_active: bool
    sent_count: int
    delivered_count: int
    effectiveness_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ProviderConfigBase(BaseModel):
    """Base model for provider configuration"""

    is_active: bool = Field(True, description="Whether provider is active")
    priority: int = Field(0, description="Provider priority (higher = preferred)")
    rate_limit: Optional[int] = Field(None, description="Messages per minute limit")
    daily_limit: Optional[int] = Field(None, description="Messages per day limit")
    cost_per_message: Optional[float] = Field(
        None, description="Base cost per message in TWD"
    )
    cost_per_segment: Optional[float] = Field(
        None, description="Additional cost per segment in TWD"
    )


class ProviderConfigUpdate(ProviderConfigBase):
    """Update model for provider configuration"""


class ProviderConfigResponse(ProviderConfigBase):
    """Response model for provider configuration"""

    id: UUID
    provider: SMSProvider
    total_sent: int
    total_failed: int
    success_rate: Optional[float]
    health_status: Optional[str] = Field(None, description="Real - time health status")
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class BulkSMSRecipient(BaseModel):
    """Model for bulk SMS recipient"""

    phone: str = Field(..., description="Recipient phone number")
    message: Optional[str] = Field(
        None, description="Custom message for this recipient"
    )
    data: Optional[Dict[str, Any]] = Field(
        None, description="Template data for this recipient"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BulkSMSRequest(BaseModel):
    """Request model for bulk SMS sending"""

    recipients: List[BulkSMSRecipient] = Field(..., description="List of recipients")
    message_type: str = Field(..., description="Message type for all recipients")
    template_code: Optional[str] = Field(
        None, description="Template to use for all recipients"
    )
    provider: Optional[SMSProvider] = Field(
        None, description="Specific provider to use"
    )

    @validator("recipients")
    def validate_recipients_limit(cls, v):
        if len(v) > 1000:
            raise ValueError("Maximum 1000 recipients per request")
        return v


class BulkSMSResponse(BaseModel):
    """Response model for bulk SMS sending"""

    total: int
    success: int
    failed: int
    errors: List[Dict[str, Any]]
