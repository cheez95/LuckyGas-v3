"""
Feature flag service for controlling feature rollout.

This service provides:
- Feature flag management
- Gradual rollout capabilities
- Per-customer feature controls
- A/B testing support
- Real-time flag updates
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.customer import Customer
from app.core.database import Base
import logging

logger = logging.getLogger(__name__)


class FeatureFlagType(str, Enum):
    """Types of feature flags."""
    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    VARIANT = "variant"
    CUSTOMER_LIST = "customer_list"


class FeatureFlagStatus(str, Enum):
    """Feature flag status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SCHEDULED = "scheduled"


class VariantConfig(BaseModel):
    """Configuration for A/B test variants."""
    name: str
    percentage: float = Field(..., ge=0, le=100)
    config: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v


class FeatureFlagConfig(BaseModel):
    """Feature flag configuration."""
    name: str
    description: str
    type: FeatureFlagType
    status: FeatureFlagStatus = FeatureFlagStatus.ACTIVE
    
    # Boolean flag
    enabled: bool = False
    
    # Percentage rollout
    percentage: float = Field(0, ge=0, le=100)
    
    # A/B test variants
    variants: List[VariantConfig] = Field(default_factory=list)
    default_variant: Optional[str] = None
    
    # Customer targeting
    enabled_customers: Set[str] = Field(default_factory=set)
    disabled_customers: Set[str] = Field(default_factory=set)
    
    # Scheduling
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator("variants")
    @classmethod
    def validate_variants(cls, v, info):
        if info.data.get("type") == FeatureFlagType.VARIANT and v:
            total_percentage = sum(variant.percentage for variant in v)
            if abs(total_percentage - 100) > 0.01:  # Allow small floating point errors
                raise ValueError(f"Variant percentages must sum to 100, got {total_percentage}")
        return v


class FeatureFlagService:
    """Service for managing feature flags."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._cache_ttl = 300  # 5 minutes
        self._flags: Dict[str, FeatureFlagConfig] = {}
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the feature flag service."""
        try:
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self._load_flags()
            logger.info("Feature flag service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize feature flag service: {e}")
            raise
            
    async def close(self):
        """Close connections."""
        if self._redis_client:
            await self._redis_client.close()
            
    async def _load_flags(self):
        """Load flags from storage."""
        # In production, this would load from database
        # For now, we'll initialize with default flags
        default_flags = [
            FeatureFlagConfig(
                name="new_ui",
                description="New React UI for customer portal",
                type=FeatureFlagType.BOOLEAN,
                enabled=False
            ),
            FeatureFlagConfig(
                name="ai_predictions",
                description="AI-powered demand predictions",
                type=FeatureFlagType.PERCENTAGE,
                percentage=10  # 10% rollout for pilot
            ),
            FeatureFlagConfig(
                name="route_optimization",
                description="Advanced route optimization algorithm",
                type=FeatureFlagType.VARIANT,
                variants=[
                    VariantConfig(name="legacy", percentage=70),
                    VariantConfig(name="new_algorithm", percentage=20),
                    VariantConfig(name="ml_based", percentage=10)
                ],
                default_variant="legacy"
            ),
            FeatureFlagConfig(
                name="pilot_program",
                description="Pilot program participants",
                type=FeatureFlagType.CUSTOMER_LIST,
                enabled_customers=set()  # Will be populated during migration
            ),
            FeatureFlagConfig(
                name="real_time_tracking",
                description="Real-time delivery tracking",
                type=FeatureFlagType.BOOLEAN,
                enabled=True
            ),
            FeatureFlagConfig(
                name="mobile_app_api",
                description="Mobile app API access",
                type=FeatureFlagType.PERCENTAGE,
                percentage=0  # Disabled by default
            )
        ]
        
        async with self._lock:
            for flag in default_flags:
                self._flags[flag.name] = flag
                
    async def get_flag(self, flag_name: str) -> Optional[FeatureFlagConfig]:
        """Get a feature flag configuration."""
        async with self._lock:
            return self._flags.get(flag_name)
            
    async def update_flag(self, flag_name: str, config: FeatureFlagConfig) -> bool:
        """Update a feature flag configuration."""
        try:
            async with self._lock:
                config.updated_at = datetime.utcnow()
                self._flags[flag_name] = config
                
            # Invalidate cache
            if self._redis_client:
                await self._redis_client.delete(f"feature_flag:{flag_name}:*")
                
            logger.info(f"Updated feature flag: {flag_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update feature flag {flag_name}: {e}")
            return False
            
    async def is_enabled(
        self,
        flag_name: str,
        customer_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if a feature is enabled for a customer."""
        flag = await self.get_flag(flag_name)
        if not flag or flag.status != FeatureFlagStatus.ACTIVE:
            return False
            
        # Check scheduling
        now = datetime.utcnow()
        if flag.start_date and now < flag.start_date:
            return False
        if flag.end_date and now > flag.end_date:
            return False
            
        # Check customer-specific rules
        if customer_id:
            if customer_id in flag.disabled_customers:
                return False
            if customer_id in flag.enabled_customers:
                return True
                
        # Handle different flag types
        if flag.type == FeatureFlagType.BOOLEAN:
            return flag.enabled
            
        elif flag.type == FeatureFlagType.PERCENTAGE:
            if not customer_id:
                return False
            # Use consistent hashing for gradual rollout
            hash_value = hash(f"{flag_name}:{customer_id}") % 100
            return hash_value < flag.percentage
            
        elif flag.type == FeatureFlagType.CUSTOMER_LIST:
            return customer_id in flag.enabled_customers if customer_id else False
            
        elif flag.type == FeatureFlagType.VARIANT:
            # For variant flags, being "enabled" means not in control group
            variant = await self.get_variant(flag_name, customer_id, attributes)
            return variant != flag.default_variant
            
        return False
        
    async def get_variant(
        self,
        flag_name: str,
        customer_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Get the variant for a customer."""
        flag = await self.get_flag(flag_name)
        if not flag or flag.status != FeatureFlagStatus.ACTIVE:
            return None
            
        if flag.type != FeatureFlagType.VARIANT:
            return None
            
        # Check cache first
        cache_key = f"feature_flag:{flag_name}:variant:{customer_id}"
        if self._redis_client and customer_id:
            cached = await self._redis_client.get(cache_key)
            if cached:
                return cached
                
        # Customer-specific overrides
        if customer_id:
            if customer_id in flag.disabled_customers:
                return flag.default_variant
            # Check if customer has a specific variant assigned
            # (This would come from database in production)
            
        # Assign variant based on percentage
        if not flag.variants:
            return flag.default_variant
            
        # Use consistent hashing for variant assignment
        if customer_id:
            hash_value = hash(f"{flag_name}:{customer_id}:variant") % 100
        else:
            hash_value = random.random() * 100
            
        cumulative = 0.0
        for variant in flag.variants:
            cumulative += variant.percentage
            if hash_value < cumulative:
                selected_variant = variant.name
                break
        else:
            selected_variant = flag.default_variant
            
        # Cache the result
        if self._redis_client and customer_id and selected_variant:
            await self._redis_client.setex(
                cache_key,
                self._cache_ttl,
                selected_variant
            )
            
        return selected_variant
        
    async def get_all_flags(self) -> Dict[str, FeatureFlagConfig]:
        """Get all feature flags."""
        async with self._lock:
            return self._flags.copy()
            
    async def get_customer_flags(
        self,
        customer_id: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get all feature flags for a customer."""
        result = {}
        
        for flag_name, flag in self._flags.items():
            if flag.status != FeatureFlagStatus.ACTIVE:
                continue
                
            if flag.type == FeatureFlagType.VARIANT:
                variant = await self.get_variant(flag_name, customer_id, attributes)
                if variant:
                    result[flag_name] = {
                        "enabled": variant != flag.default_variant,
                        "variant": variant
                    }
            else:
                enabled = await self.is_enabled(flag_name, customer_id, attributes)
                result[flag_name] = {"enabled": enabled}
                
        return result
        
    async def add_customer_to_flag(
        self,
        flag_name: str,
        customer_id: str,
        enabled: bool = True
    ) -> bool:
        """Add a customer to a feature flag."""
        flag = await self.get_flag(flag_name)
        if not flag:
            return False
            
        async with self._lock:
            if enabled:
                flag.enabled_customers.add(customer_id)
                flag.disabled_customers.discard(customer_id)
            else:
                flag.disabled_customers.add(customer_id)
                flag.enabled_customers.discard(customer_id)
                
        # Invalidate cache
        if self._redis_client:
            await self._redis_client.delete(f"feature_flag:{flag_name}:*")
            
        return True
        
    async def remove_customer_from_flag(
        self,
        flag_name: str,
        customer_id: str
    ) -> bool:
        """Remove a customer from a feature flag."""
        flag = await self.get_flag(flag_name)
        if not flag:
            return False
            
        async with self._lock:
            flag.enabled_customers.discard(customer_id)
            flag.disabled_customers.discard(customer_id)
            
        # Invalidate cache
        if self._redis_client:
            await self._redis_client.delete(f"feature_flag:{flag_name}:*")
            
        return True
        
    async def get_pilot_customers(self) -> Set[str]:
        """Get all customers in the pilot program."""
        flag = await self.get_flag("pilot_program")
        if flag and flag.type == FeatureFlagType.CUSTOMER_LIST:
            return flag.enabled_customers
        return set()
        
    async def add_pilot_customer(self, customer_id: str) -> bool:
        """Add a customer to the pilot program."""
        return await self.add_customer_to_flag("pilot_program", customer_id, True)
        
    async def remove_pilot_customer(self, customer_id: str) -> bool:
        """Remove a customer from the pilot program."""
        return await self.remove_customer_from_flag("pilot_program", customer_id)
        
    async def update_percentage_rollout(
        self,
        flag_name: str,
        percentage: float
    ) -> bool:
        """Update the percentage rollout for a flag."""
        flag = await self.get_flag(flag_name)
        if not flag or flag.type != FeatureFlagType.PERCENTAGE:
            return False
            
        flag.percentage = percentage
        return await self.update_flag(flag_name, flag)


# Global instance
_feature_flag_service: Optional[FeatureFlagService] = None


async def get_feature_flag_service() -> FeatureFlagService:
    """Get the feature flag service instance."""
    global _feature_flag_service
    if _feature_flag_service is None:
        _feature_flag_service = FeatureFlagService()
        await _feature_flag_service.initialize()
    return _feature_flag_service


@asynccontextmanager
async def feature_flag_context():
    """Context manager for feature flag service."""
    service = await get_feature_flag_service()
    try:
        yield service
    finally:
        pass  # Service cleanup handled at app shutdown