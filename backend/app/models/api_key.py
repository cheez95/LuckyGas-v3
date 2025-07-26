"""
API Key model for B2B partner authentication
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True, index=True)  # SHA256 hash
    key_prefix = Column(String, nullable=False)  # First 8 chars for identification
    scopes = Column(JSON, nullable=False, default=list)  # List of permission scopes
    
    # Rate limiting
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Metadata
    description = Column(String, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Security
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # IP restrictions (optional)
    allowed_ips = Column(JSON, nullable=True)  # List of allowed IP addresses
    
    # Partner information
    partner_name = Column(String, nullable=True)
    partner_email = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, nullable=False)  # User ID who created the key