"""
Pydantic schemas for API key management.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(
        ..., description="Descriptive name for the API key", max_length=100
    )
    tier: str = Field(
        "basic", description="Rate limiting tier (basic, standard, premium, enterprise)"
    )

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("API key name cannot be empty")
        return v.strip()


class APIKeyResponse(BaseModel):
    """Response schema for API key creation."""

    api_key: str = Field(..., description="The generated API key (only shown once)")
    key_hash: str = Field(..., description="Hash of the API key for future reference")
    name: str = Field(..., description="Name of the API key")
    tier: str = Field(..., description="Rate limiting tier")
    rate_limits: Dict[str, Any] = Field(
        ..., description="Rate limit configuration for this tier"
    )
    message: str = Field(..., description="Important message about key storage")


class APIKeyListResponse(BaseModel):
    """Response schema for listing API keys."""

    key_hash: str = Field(..., description="Hash of the API key")
    name: str = Field(..., description="Name of the API key")
    tier: str = Field(..., description="Rate limiting tier")
    created_at: str = Field(..., description="When the key was created")
    last_used: Optional[str] = Field(None, description="When the key was last used")
    usage_count: int = Field(
        0, description="Total number of requests made with this key"
    )
    active: bool = Field(True, description="Whether the key is currently active")


class APIKeyRevoke(BaseModel):
    """Schema for revoking an API key."""

    key_hash: str = Field(..., description="Hash of the API key to revoke")
    reason: Optional[str] = Field(None, description="Reason for revocation")


class APIKeyUsageResponse(BaseModel):
    """Response schema for API key usage statistics."""

    key_hash: str
    name: str
    tier: str
    usage: Dict[str, Any] = Field(..., description="Current usage statistics")


class RateLimitStatus(BaseModel):
    """Current rate limit status."""

    limit: int = Field(..., description="Maximum requests allowed")
    remaining: int = Field(..., description="Remaining requests in current window")
    reset: datetime = Field(..., description="When the rate limit window resets")
    retry_after: Optional[int] = Field(
        None, description="Seconds to wait before retry (when rate limited)"
    )


class RateLimitExceededResponse(BaseModel):
    """Response when rate limit is exceeded."""

    detail: str = Field("請求次數超過限制")
    error: str = Field("rate_limit_exceeded")
    retry_after: int = Field(..., description="Seconds to wait before retry")
    limit: int = Field(..., description="Your rate limit")
    remaining: int = Field(0, description="Remaining requests (0)")
    reset: datetime = Field(..., description="When your rate limit resets")
