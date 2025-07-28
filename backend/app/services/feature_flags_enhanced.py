"""
Enhanced feature flag service with persistence and audit trail.

This service provides:
- Database persistence for all feature flags
- Complete audit trail of all changes
- Performance tracking and analytics
- Real-time flag updates with cache invalidation
- Customer-specific targeting with history
"""

import json
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from contextlib import asynccontextmanager
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload, joinedload
import redis.asyncio as redis
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.customer import Customer
from app.models.feature_flag import (
    FeatureFlag as FeatureFlagModel,
    FeatureFlagVariant as VariantModel,
    FeatureFlagAudit as AuditModel,
    FeatureFlagEvaluation as EvaluationModel,
    FeatureFlagType, FeatureFlagStatus, AuditAction,
    feature_flag_enabled_customers,
    feature_flag_disabled_customers
)
import logging

logger = logging.getLogger(__name__)


class VariantCreate(BaseModel):
    """Schema for creating variants."""
    name: str
    percentage: float = Field(..., ge=0, le=100)
    config: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class FeatureFlagCreate(BaseModel):
    """Schema for creating feature flags."""
    name: str
    description: str
    type: FeatureFlagType
    status: FeatureFlagStatus = FeatureFlagStatus.INACTIVE
    
    # Boolean flag
    enabled: bool = False
    
    # Percentage rollout
    percentage: float = Field(0, ge=0, le=100)
    
    # A/B test variants
    variants: List[VariantCreate] = Field(default_factory=list)
    
    # Scheduling
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator("variants")
    @classmethod
    def validate_variants(cls, v, info):
        if info.data.get("type") == FeatureFlagType.VARIANT and v:
            total_percentage = sum(variant.percentage for variant in v)
            if abs(total_percentage - 100) > 0.01:
                raise ValueError(f"Variant percentages must sum to 100, got {total_percentage}")
        return v


class FeatureFlagUpdate(BaseModel):
    """Schema for updating feature flags."""
    description: Optional[str] = None
    status: Optional[FeatureFlagStatus] = None
    enabled: Optional[bool] = None
    percentage: Optional[float] = Field(None, ge=0, le=100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class EvaluationContext(BaseModel):
    """Context for feature flag evaluation."""
    customer_id: Optional[str] = None
    user_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None


class EnhancedFeatureFlagService:
    """Enhanced feature flag service with full persistence and audit trail."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._cache_ttl = 300  # 5 minutes
        self._evaluation_batch_size = 100
        self._evaluation_queue: List[EvaluationModel] = []
        self._evaluation_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the enhanced feature flag service."""
        try:
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Start evaluation flush task
            self._flush_task = asyncio.create_task(self._evaluation_flush_worker())
            
            # Load and migrate existing flags
            await self._migrate_existing_flags()
            
            logger.info("Enhanced feature flag service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize feature flag service: {e}")
            raise
            
    async def close(self):
        """Close the service."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
                
        # Flush remaining evaluations
        await self._flush_evaluations()
        
        if self._redis_client:
            await self._redis_client.close()
            
    async def _migrate_existing_flags(self):
        """Migrate default flags to database if not exists."""
        async with async_session_maker() as db:
            # Check if flags already exist
            result = await db.execute(select(func.count(FeatureFlagModel.id)))
            count = result.scalar()
            
            if count > 0:
                return  # Already migrated
                
            # Create default flags
            default_flags = [
                {
                    "name": "new_ui",
                    "description": "New React UI for customer portal",
                    "type": FeatureFlagType.BOOLEAN,
                    "enabled": False
                },
                {
                    "name": "ai_predictions",
                    "description": "AI-powered demand predictions",
                    "type": FeatureFlagType.PERCENTAGE,
                    "percentage": 10
                },
                {
                    "name": "route_optimization",
                    "description": "Advanced route optimization algorithm",
                    "type": FeatureFlagType.VARIANT,
                    "variants": [
                        VariantCreate(name="legacy", percentage=70, is_default=True),
                        VariantCreate(name="new_algorithm", percentage=20),
                        VariantCreate(name="ml_based", percentage=10)
                    ]
                },
                {
                    "name": "pilot_program",
                    "description": "Pilot program participants",
                    "type": FeatureFlagType.CUSTOMER_LIST
                },
                {
                    "name": "real_time_tracking",
                    "description": "Real-time delivery tracking",
                    "type": FeatureFlagType.BOOLEAN,
                    "enabled": True,
                    "status": FeatureFlagStatus.ACTIVE
                },
                {
                    "name": "mobile_app_api",
                    "description": "Mobile app API access",
                    "type": FeatureFlagType.PERCENTAGE,
                    "percentage": 0
                }
            ]
            
            for flag_data in default_flags:
                variants = flag_data.pop("variants", [])
                status = flag_data.pop("status", FeatureFlagStatus.INACTIVE)
                
                flag = FeatureFlagModel(
                    id=str(uuid.uuid4()),
                    status=status,
                    **flag_data
                )
                db.add(flag)
                
                # Add variants if any
                for variant_data in variants:
                    variant = VariantModel(
                        id=str(uuid.uuid4()),
                        feature_flag_id=flag.id,
                        name=variant_data.name,
                        percentage=variant_data.percentage,
                        config=variant_data.config,
                        is_default=variant_data.is_default
                    )
                    db.add(variant)
                    
                # Add audit entry
                audit = AuditModel(
                    id=str(uuid.uuid4()),
                    feature_flag_id=flag.id,
                    action=AuditAction.CREATED,
                    new_value=flag_data,
                    details={"migration": True}
                )
                db.add(audit)
                
            await db.commit()
            logger.info("Migrated default feature flags to database")
            
    async def _evaluation_flush_worker(self):
        """Background worker to flush evaluation records."""
        while True:
            try:
                await asyncio.sleep(10)  # Flush every 10 seconds
                await self._flush_evaluations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Evaluation flush error: {e}")
                
    async def _flush_evaluations(self):
        """Flush evaluation records to database."""
        async with self._evaluation_lock:
            if not self._evaluation_queue:
                return
                
            evaluations = self._evaluation_queue[:self._evaluation_batch_size]
            self._evaluation_queue = self._evaluation_queue[self._evaluation_batch_size:]
            
        try:
            async with async_session_maker() as db:
                db.add_all(evaluations)
                await db.commit()
                
                # Update evaluation counts
                flag_counts = {}
                for eval in evaluations:
                    flag_counts[eval.feature_flag_id] = flag_counts.get(eval.feature_flag_id, 0) + 1
                    
                for flag_id, count in flag_counts.items():
                    await db.execute(
                        update(FeatureFlagModel)
                        .where(FeatureFlagModel.id == flag_id)
                        .values(
                            evaluation_count=FeatureFlagModel.evaluation_count + count,
                            last_evaluated_at=datetime.utcnow()
                        )
                    )
                    
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to flush evaluations: {e}")
            
    async def create_flag(
        self,
        flag_data: FeatureFlagCreate,
        created_by: Optional[str] = None,
        context: Optional[EvaluationContext] = None
    ) -> str:
        """Create a new feature flag."""
        async with async_session_maker() as db:
            # Check if flag already exists
            existing = await db.execute(
                select(FeatureFlagModel).where(FeatureFlagModel.name == flag_data.name)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Feature flag '{flag_data.name}' already exists")
                
            # Create flag
            flag = FeatureFlagModel(
                id=str(uuid.uuid4()),
                name=flag_data.name,
                description=flag_data.description,
                type=flag_data.type,
                status=flag_data.status,
                enabled=flag_data.enabled,
                percentage=flag_data.percentage,
                start_date=flag_data.start_date,
                end_date=flag_data.end_date,
                tags=flag_data.tags,
                config=flag_data.config,
                created_by=created_by
            )
            db.add(flag)
            
            # Add variants
            for variant_data in flag_data.variants:
                variant = VariantModel(
                    id=str(uuid.uuid4()),
                    feature_flag_id=flag.id,
                    name=variant_data.name,
                    percentage=variant_data.percentage,
                    config=variant_data.config,
                    is_default=variant_data.is_default
                )
                db.add(variant)
                
            # Add audit entry
            audit = AuditModel(
                id=str(uuid.uuid4()),
                feature_flag_id=flag.id,
                action=AuditAction.CREATED,
                user_id=created_by,
                new_value=flag_data.model_dump(),
                ip_address=context.ip_address if context else None,
                user_agent=context.user_agent if context else None,
                request_id=context.request_id if context else None
            )
            db.add(audit)
            
            await db.commit()
            
            # Invalidate cache
            await self._invalidate_cache(flag.name)
            
            logger.info(f"Created feature flag: {flag.name}")
            return flag.id
            
    async def update_flag(
        self,
        flag_name: str,
        update_data: FeatureFlagUpdate,
        updated_by: Optional[str] = None,
        context: Optional[EvaluationContext] = None
    ) -> bool:
        """Update a feature flag."""
        async with async_session_maker() as db:
            # Get flag with lock
            result = await db.execute(
                select(FeatureFlagModel)
                .where(FeatureFlagModel.name == flag_name)
                .with_for_update()
            )
            flag = result.scalar_one_or_none()
            
            if not flag:
                return False
                
            # Store old values for audit
            old_values = {
                "description": flag.description,
                "status": flag.status.value if flag.status else None,
                "enabled": flag.enabled,
                "percentage": flag.percentage,
                "start_date": flag.start_date.isoformat() if flag.start_date else None,
                "end_date": flag.end_date.isoformat() if flag.end_date else None,
                "tags": flag.tags,
                "config": flag.config
            }
            
            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            new_values = {}
            
            for field, value in update_dict.items():
                if value is not None:
                    setattr(flag, field, value)
                    new_values[field] = value.value if hasattr(value, 'value') else value
                    
            flag.updated_by = updated_by
            flag.updated_at = datetime.utcnow()
            
            # Determine audit action
            action = AuditAction.UPDATED
            if "status" in update_dict:
                if update_dict["status"] == FeatureFlagStatus.ACTIVE:
                    action = AuditAction.ACTIVATED
                elif update_dict["status"] == FeatureFlagStatus.INACTIVE:
                    action = AuditAction.DEACTIVATED
            elif "percentage" in update_dict:
                action = AuditAction.PERCENTAGE_CHANGED
                
            # Add audit entry
            audit = AuditModel(
                id=str(uuid.uuid4()),
                feature_flag_id=flag.id,
                action=action,
                user_id=updated_by,
                old_value=old_values,
                new_value=new_values,
                ip_address=context.ip_address if context else None,
                user_agent=context.user_agent if context else None,
                request_id=context.request_id if context else None
            )
            db.add(audit)
            
            await db.commit()
            
            # Invalidate cache
            await self._invalidate_cache(flag_name)
            
            logger.info(f"Updated feature flag: {flag_name}")
            return True
            
    async def delete_flag(
        self,
        flag_name: str,
        deleted_by: Optional[str] = None,
        context: Optional[EvaluationContext] = None
    ) -> bool:
        """Archive a feature flag (soft delete)."""
        async with async_session_maker() as db:
            result = await db.execute(
                select(FeatureFlagModel)
                .where(FeatureFlagModel.name == flag_name)
                .with_for_update()
            )
            flag = result.scalar_one_or_none()
            
            if not flag:
                return False
                
            # Archive instead of delete
            flag.status = FeatureFlagStatus.ARCHIVED
            flag.updated_by = deleted_by
            flag.updated_at = datetime.utcnow()
            
            # Add audit entry
            audit = AuditModel(
                id=str(uuid.uuid4()),
                feature_flag_id=flag.id,
                action=AuditAction.DELETED,
                user_id=deleted_by,
                old_value={"status": flag.status.value},
                new_value={"status": FeatureFlagStatus.ARCHIVED.value},
                ip_address=context.ip_address if context else None,
                user_agent=context.user_agent if context else None,
                request_id=context.request_id if context else None
            )
            db.add(audit)
            
            await db.commit()
            
            # Invalidate cache
            await self._invalidate_cache(flag_name)
            
            logger.info(f"Archived feature flag: {flag_name}")
            return True
            
    async def get_flag(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get a feature flag configuration."""
        # Check cache first
        cache_key = f"feature_flag:{flag_name}"
        if self._redis_client:
            cached = await self._redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
                
        # Get from database
        async with async_session_maker() as db:
            result = await db.execute(
                select(FeatureFlagModel)
                .options(
                    selectinload(FeatureFlagModel.variants),
                    selectinload(FeatureFlagModel.enabled_customers),
                    selectinload(FeatureFlagModel.disabled_customers)
                )
                .where(FeatureFlagModel.name == flag_name)
            )
            flag = result.scalar_one_or_none()
            
            if not flag:
                return None
                
            flag_dict = flag.to_dict()
            
            # Cache the result
            if self._redis_client:
                await self._redis_client.setex(
                    cache_key,
                    self._cache_ttl,
                    json.dumps(flag_dict)
                )
                
            return flag_dict
            
    async def is_enabled(
        self,
        flag_name: str,
        context: Optional[EvaluationContext] = None,
        skip_evaluation: bool = False
    ) -> bool:
        """Check if a feature is enabled."""
        flag = await self.get_flag(flag_name)
        if not flag or flag["status"] != FeatureFlagStatus.ACTIVE.value:
            return False
            
        # Check scheduling
        now = datetime.utcnow()
        if flag["start_date"]:
            start_date = datetime.fromisoformat(flag["start_date"])
            if now < start_date:
                return False
        if flag["end_date"]:
            end_date = datetime.fromisoformat(flag["end_date"])
            if now > end_date:
                return False
                
        # Determine result
        enabled = False
        reason = "default"
        
        # Check customer-specific rules
        if context and context.customer_id:
            # Check if customer is in disabled list
            async with async_session_maker() as db:
                disabled_result = await db.execute(
                    select(func.count())
                    .select_from(feature_flag_disabled_customers)
                    .where(
                        and_(
                            feature_flag_disabled_customers.c.feature_flag_id == flag["id"],
                            feature_flag_disabled_customers.c.customer_id == context.customer_id
                        )
                    )
                )
                if disabled_result.scalar() > 0:
                    enabled = False
                    reason = "customer_disabled"
                else:
                    # Check if customer is in enabled list
                    enabled_result = await db.execute(
                        select(func.count())
                        .select_from(feature_flag_enabled_customers)
                        .where(
                            and_(
                                feature_flag_enabled_customers.c.feature_flag_id == flag["id"],
                                feature_flag_enabled_customers.c.customer_id == context.customer_id
                            )
                        )
                    )
                    if enabled_result.scalar() > 0:
                        enabled = True
                        reason = "customer_enabled"
                        
        # If not customer-specific, use flag type logic
        if reason == "default":
            if flag["type"] == FeatureFlagType.BOOLEAN.value:
                enabled = flag["enabled"]
                reason = "boolean_flag"
                
            elif flag["type"] == FeatureFlagType.PERCENTAGE.value:
                if context and context.customer_id:
                    # Use consistent hashing
                    hash_value = hash(f"{flag_name}:{context.customer_id}") % 100
                    enabled = hash_value < flag["percentage"]
                    reason = f"percentage_rollout_{flag['percentage']}%"
                else:
                    enabled = False
                    reason = "no_customer_id"
                    
            elif flag["type"] == FeatureFlagType.CUSTOMER_LIST.value:
                # Already handled above
                enabled = False
                reason = "not_in_list"
                
            elif flag["type"] == FeatureFlagType.VARIANT.value:
                # For variant flags, being "enabled" means not in control group
                variant = await self._get_variant(flag, context)
                enabled = not any(v["is_default"] for v in flag["variants"] if v["name"] == variant)
                reason = f"variant_{variant}"
                
        # Record evaluation if not skipped
        if not skip_evaluation and context:
            await self._record_evaluation(
                flag["id"],
                context,
                enabled,
                None,
                reason
            )
            
        return enabled
        
    async def get_variant(
        self,
        flag_name: str,
        context: Optional[EvaluationContext] = None,
        skip_evaluation: bool = False
    ) -> Optional[str]:
        """Get the variant for a customer."""
        flag = await self.get_flag(flag_name)
        if not flag or flag["status"] != FeatureFlagStatus.ACTIVE.value:
            return None
            
        if flag["type"] != FeatureFlagType.VARIANT.value:
            return None
            
        variant = await self._get_variant(flag, context)
        
        # Record evaluation if not skipped
        if not skip_evaluation and context:
            enabled = not any(v["is_default"] for v in flag["variants"] if v["name"] == variant)
            await self._record_evaluation(
                flag["id"],
                context,
                enabled,
                variant,
                f"variant_assigned"
            )
            
        return variant
        
    async def _get_variant(
        self,
        flag: Dict[str, Any],
        context: Optional[EvaluationContext]
    ) -> Optional[str]:
        """Internal method to get variant."""
        # Check cache first
        cache_key = None
        if self._redis_client and context and context.customer_id:
            cache_key = f"feature_flag:{flag['name']}:variant:{context.customer_id}"
            cached = await self._redis_client.get(cache_key)
            if cached:
                return cached
                
        # Find default variant
        default_variant = next(
            (v["name"] for v in flag["variants"] if v["is_default"]),
            flag["variants"][0]["name"] if flag["variants"] else None
        )
        
        if not default_variant:
            return None
            
        # Customer-specific overrides
        if context and context.customer_id:
            # Check if customer has override (would be in customer assignments)
            # For now, use percentage-based assignment
            pass
            
        # Assign variant based on percentage
        if context and context.customer_id:
            hash_value = hash(f"{flag['name']}:{context.customer_id}:variant") % 100
        else:
            hash_value = random.random() * 100
            
        cumulative = 0.0
        selected_variant = default_variant
        
        for variant in flag["variants"]:
            cumulative += variant["percentage"]
            if hash_value < cumulative:
                selected_variant = variant["name"]
                break
                
        # Cache the result
        if cache_key and self._redis_client:
            await self._redis_client.setex(
                cache_key,
                self._cache_ttl,
                selected_variant
            )
            
        return selected_variant
        
    async def _record_evaluation(
        self,
        flag_id: str,
        context: EvaluationContext,
        enabled: bool,
        variant: Optional[str],
        reason: str
    ):
        """Record a feature flag evaluation."""
        evaluation = EvaluationModel(
            id=str(uuid.uuid4()),
            feature_flag_id=flag_id,
            customer_id=context.customer_id,
            user_id=context.user_id,
            timestamp=datetime.utcnow(),
            enabled=enabled,
            variant=variant,
            reason=reason,
            attributes=context.attributes,
            evaluation_time_ms=0  # Would measure actual time
        )
        
        async with self._evaluation_lock:
            self._evaluation_queue.append(evaluation)
            
    async def add_customer_to_flag(
        self,
        flag_name: str,
        customer_id: str,
        enabled: bool = True,
        added_by: Optional[str] = None,
        context: Optional[EvaluationContext] = None
    ) -> bool:
        """Add a customer to a feature flag."""
        async with async_session_maker() as db:
            # Get flag
            result = await db.execute(
                select(FeatureFlagModel).where(FeatureFlagModel.name == flag_name)
            )
            flag = result.scalar_one_or_none()
            
            if not flag:
                return False
                
            if enabled:
                # Remove from disabled if present
                await db.execute(
                    feature_flag_disabled_customers.delete().where(
                        and_(
                            feature_flag_disabled_customers.c.feature_flag_id == flag.id,
                            feature_flag_disabled_customers.c.customer_id == customer_id
                        )
                    )
                )
                
                # Add to enabled
                try:
                    await db.execute(
                        feature_flag_enabled_customers.insert().values(
                            feature_flag_id=flag.id,
                            customer_id=customer_id,
                            enabled_by=added_by
                        )
                    )
                except:
                    # Already exists
                    pass
                    
                action = AuditAction.CUSTOMER_ADDED
                
            else:
                # Remove from enabled if present
                await db.execute(
                    feature_flag_enabled_customers.delete().where(
                        and_(
                            feature_flag_enabled_customers.c.feature_flag_id == flag.id,
                            feature_flag_enabled_customers.c.customer_id == customer_id
                        )
                    )
                )
                
                # Add to disabled
                try:
                    await db.execute(
                        feature_flag_disabled_customers.insert().values(
                            feature_flag_id=flag.id,
                            customer_id=customer_id,
                            disabled_by=added_by
                        )
                    )
                except:
                    # Already exists
                    pass
                    
                action = AuditAction.CUSTOMER_REMOVED
                
            # Add audit entry
            audit = AuditModel(
                id=str(uuid.uuid4()),
                feature_flag_id=flag.id,
                action=action,
                user_id=added_by,
                details={"customer_id": customer_id, "enabled": enabled},
                ip_address=context.ip_address if context else None,
                user_agent=context.user_agent if context else None,
                request_id=context.request_id if context else None
            )
            db.add(audit)
            
            await db.commit()
            
            # Invalidate cache
            await self._invalidate_cache(flag_name)
            if self._redis_client:
                await self._redis_client.delete(f"feature_flag:{flag_name}:variant:{customer_id}")
                
            return True
            
    async def remove_customer_from_flag(
        self,
        flag_name: str,
        customer_id: str,
        removed_by: Optional[str] = None,
        context: Optional[EvaluationContext] = None
    ) -> bool:
        """Remove a customer from a feature flag."""
        async with async_session_maker() as db:
            # Get flag
            result = await db.execute(
                select(FeatureFlagModel).where(FeatureFlagModel.name == flag_name)
            )
            flag = result.scalar_one_or_none()
            
            if not flag:
                return False
                
            # Remove from both lists
            await db.execute(
                feature_flag_enabled_customers.delete().where(
                    and_(
                        feature_flag_enabled_customers.c.feature_flag_id == flag.id,
                        feature_flag_enabled_customers.c.customer_id == customer_id
                    )
                )
            )
            
            await db.execute(
                feature_flag_disabled_customers.delete().where(
                    and_(
                        feature_flag_disabled_customers.c.feature_flag_id == flag.id,
                        feature_flag_disabled_customers.c.customer_id == customer_id
                    )
                )
            )
            
            # Add audit entry
            audit = AuditModel(
                id=str(uuid.uuid4()),
                feature_flag_id=flag.id,
                action=AuditAction.CUSTOMER_REMOVED,
                user_id=removed_by,
                details={"customer_id": customer_id, "removed": True},
                ip_address=context.ip_address if context else None,
                user_agent=context.user_agent if context else None,
                request_id=context.request_id if context else None
            )
            db.add(audit)
            
            await db.commit()
            
            # Invalidate cache
            await self._invalidate_cache(flag_name)
            if self._redis_client:
                await self._redis_client.delete(f"feature_flag:{flag_name}:variant:{customer_id}")
                
            return True
            
    async def get_all_flags(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get all feature flags."""
        async with async_session_maker() as db:
            query = select(FeatureFlagModel).options(
                selectinload(FeatureFlagModel.variants)
            )
            
            if not include_archived:
                query = query.where(FeatureFlagModel.status != FeatureFlagStatus.ARCHIVED)
                
            result = await db.execute(query.order_by(FeatureFlagModel.name))
            flags = result.scalars().all()
            
            return [flag.to_dict() for flag in flags]
            
    async def get_customer_flags(
        self,
        customer_id: str,
        context: Optional[EvaluationContext] = None
    ) -> Dict[str, Any]:
        """Get all feature flags for a customer."""
        if not context:
            context = EvaluationContext(customer_id=customer_id)
            
        flags = await self.get_all_flags()
        result = {}
        
        for flag in flags:
            if flag["status"] != FeatureFlagStatus.ACTIVE.value:
                continue
                
            flag_name = flag["name"]
            
            if flag["type"] == FeatureFlagType.VARIANT.value:
                variant = await self.get_variant(flag_name, context, skip_evaluation=True)
                if variant:
                    is_enabled = not any(
                        v["is_default"] for v in flag["variants"] if v["name"] == variant
                    )
                    result[flag_name] = {
                        "enabled": is_enabled,
                        "variant": variant
                    }
            else:
                enabled = await self.is_enabled(flag_name, context, skip_evaluation=True)
                result[flag_name] = {"enabled": enabled}
                
        return result
        
    async def get_flag_audit_trail(
        self,
        flag_name: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get audit trail for a feature flag."""
        async with async_session_maker() as db:
            # Get flag
            flag_result = await db.execute(
                select(FeatureFlagModel).where(FeatureFlagModel.name == flag_name)
            )
            flag = flag_result.scalar_one_or_none()
            
            if not flag:
                return []
                
            # Get audit entries
            result = await db.execute(
                select(AuditModel)
                .options(joinedload(AuditModel.user))
                .where(AuditModel.feature_flag_id == flag.id)
                .order_by(AuditModel.timestamp.desc())
                .offset(offset)
                .limit(limit)
            )
            audits = result.scalars().all()
            
            return [audit.to_dict() for audit in audits]
            
    async def get_flag_analytics(
        self,
        flag_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get analytics for a feature flag."""
        async with async_session_maker() as db:
            # Get flag
            flag_result = await db.execute(
                select(FeatureFlagModel).where(FeatureFlagModel.name == flag_name)
            )
            flag = flag_result.scalar_one_or_none()
            
            if not flag:
                return {}
                
            # Build query
            query = select(
                func.count(EvaluationModel.id).label("total_evaluations"),
                func.sum(func.cast(EvaluationModel.enabled, Integer)).label("enabled_count"),
                func.avg(EvaluationModel.evaluation_time_ms).label("avg_eval_time_ms")
            ).where(EvaluationModel.feature_flag_id == flag.id)
            
            if start_date:
                query = query.where(EvaluationModel.timestamp >= start_date)
            if end_date:
                query = query.where(EvaluationModel.timestamp <= end_date)
                
            result = await db.execute(query)
            stats = result.one()
            
            # Get variant distribution if applicable
            variant_stats = {}
            if flag.type == FeatureFlagType.VARIANT:
                variant_result = await db.execute(
                    select(
                        EvaluationModel.variant,
                        func.count(EvaluationModel.id).label("count")
                    )
                    .where(EvaluationModel.feature_flag_id == flag.id)
                    .group_by(EvaluationModel.variant)
                )
                variant_stats = {
                    variant: count
                    for variant, count in variant_result
                }
                
            return {
                "flag_name": flag_name,
                "total_evaluations": stats.total_evaluations or 0,
                "enabled_count": stats.enabled_count or 0,
                "disabled_count": (stats.total_evaluations or 0) - (stats.enabled_count or 0),
                "enabled_percentage": (
                    (stats.enabled_count / stats.total_evaluations * 100)
                    if stats.total_evaluations else 0
                ),
                "avg_evaluation_time_ms": float(stats.avg_eval_time_ms or 0),
                "variant_distribution": variant_stats,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
            
    async def _invalidate_cache(self, flag_name: str):
        """Invalidate all cache entries for a flag."""
        if self._redis_client:
            # Get all keys matching pattern
            pattern = f"feature_flag:{flag_name}*"
            cursor = 0
            
            while True:
                cursor, keys = await self._redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                if keys:
                    await self._redis_client.delete(*keys)
                    
                if cursor == 0:
                    break
                    
    # Convenience methods for backward compatibility
    
    async def get_pilot_customers(self) -> Set[str]:
        """Get all customers in the pilot program."""
        async with async_session_maker() as db:
            result = await db.execute(
                select(FeatureFlagModel)
                .options(selectinload(FeatureFlagModel.enabled_customers))
                .where(FeatureFlagModel.name == "pilot_program")
            )
            flag = result.scalar_one_or_none()
            
            if flag:
                return {c.id for c in flag.enabled_customers}
                
        return set()
        
    async def add_pilot_customer(
        self,
        customer_id: str,
        added_by: Optional[str] = None,
        context: Optional[EvaluationContext] = None
    ) -> bool:
        """Add a customer to the pilot program."""
        return await self.add_customer_to_flag(
            "pilot_program",
            customer_id,
            True,
            added_by,
            context
        )
        
    async def remove_pilot_customer(
        self,
        customer_id: str,
        removed_by: Optional[str] = None,
        context: Optional[EvaluationContext] = None
    ) -> bool:
        """Remove a customer from the pilot program."""
        return await self.remove_customer_from_flag(
            "pilot_program",
            customer_id,
            removed_by,
            context
        )
        
    async def update_percentage_rollout(
        self,
        flag_name: str,
        percentage: float,
        updated_by: Optional[str] = None,
        context: Optional[EvaluationContext] = None
    ) -> bool:
        """Update the percentage rollout for a flag."""
        update_data = FeatureFlagUpdate(percentage=percentage)
        return await self.update_flag(flag_name, update_data, updated_by, context)


# Global instance
_feature_flag_service: Optional[EnhancedFeatureFlagService] = None


async def get_feature_flag_service() -> EnhancedFeatureFlagService:
    """Get the enhanced feature flag service instance."""
    global _feature_flag_service
    if _feature_flag_service is None:
        _feature_flag_service = EnhancedFeatureFlagService()
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