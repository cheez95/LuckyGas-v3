"""
Admin API endpoints for migration monitoring and control.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.auth import require_admin
from app.models.customer import Customer
from app.models.user import User
from app.services.feature_flags import get_feature_flag_service, FeatureFlagConfig
from app.services.sync_service import (
    get_sync_service,
    SyncOperation,
    SyncStatus,
    ConflictResolution,
    SyncMetrics as ServiceSyncMetrics
)
from app.core.logging import logger


router = APIRouter(prefix="/admin/migration", tags=["admin-migration"])


class MigrationMetrics(BaseModel):
    """Migration metrics response."""
    totalCustomers: int
    migratedCustomers: int
    pendingCustomers: int
    failedCustomers: int
    successRate: float
    averageSyncTime: float
    lastSyncAt: Optional[str]
    estimatedCompletion: Optional[str]


class CustomerSelectionRequest(BaseModel):
    """Customer selection criteria."""
    percentage: float = Field(..., ge=0, le=100)
    minOrderCount: Optional[int] = None
    region: Optional[str] = None
    customerType: Optional[str] = None


class CustomerSelectionResponse(BaseModel):
    """Customer selection response."""
    customerIds: List[str]
    count: int


class MigrationStartRequest(BaseModel):
    """Migration start request."""
    customerIds: List[str]
    batchSize: int = Field(50, ge=1, le=500)


class ConflictResolutionRequest(BaseModel):
    """Conflict resolution request."""
    resolution: ConflictResolution
    resolvedData: Optional[Dict[str, Any]] = None


class FeatureFlagUpdateRequest(BaseModel):
    """Feature flag update request."""
    status: Optional[str] = None
    percentage: Optional[float] = Field(None, ge=0, le=100)
    enabledCustomers: Optional[List[str]] = None


@router.get("/metrics", response_model=MigrationMetrics)
async def get_migration_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
) -> MigrationMetrics:
    """Get current migration metrics."""
    try:
        # Get total customers
        total_result = await db.execute(
            select(func.count(Customer.id))
        )
        total_customers = total_result.scalar() or 0
        
        # Get migrated customers (in pilot program)
        migrated_result = await db.execute(
            select(func.count(Customer.id))
            .where(Customer.in_pilot_program == True)
        )
        migrated_customers = migrated_result.scalar() or 0
        
        # Get sync service metrics
        sync_service = await get_sync_service()
        sync_metrics = await sync_service.get_metrics()
        
        # Calculate aggregate metrics
        total_synced = sum(m.total_synced for m in sync_metrics.values())
        successful = sum(m.successful for m in sync_metrics.values())
        failed = sum(m.failed for m in sync_metrics.values())
        pending = total_customers - migrated_customers
        
        # Calculate average sync time
        avg_times = [m.average_sync_time_ms for m in sync_metrics.values() if m.average_sync_time_ms > 0]
        avg_sync_time = sum(avg_times) / len(avg_times) if avg_times else 0
        
        # Get last sync time
        last_syncs = [m.last_sync_at for m in sync_metrics.values() if m.last_sync_at]
        last_sync = max(last_syncs) if last_syncs else None
        
        # Calculate success rate
        success_rate = (successful / total_synced * 100) if total_synced > 0 else 0
        
        # Estimate completion time
        if migrated_customers > 0 and pending > 0:
            # Calculate migration rate (customers per hour)
            # This is simplified - in production would use actual timestamps
            migration_rate = migrated_customers / 24  # Assume 24 hours
            hours_remaining = pending / migration_rate if migration_rate > 0 else 0
            estimated_completion = datetime.utcnow() + timedelta(hours=hours_remaining)
        else:
            estimated_completion = None
            
        return MigrationMetrics(
            totalCustomers=total_customers,
            migratedCustomers=migrated_customers,
            pendingCustomers=pending,
            failedCustomers=failed,
            successRate=success_rate,
            averageSyncTime=avg_sync_time,
            lastSyncAt=last_sync.isoformat() if last_sync else None,
            estimatedCompletion=estimated_completion.isoformat() if estimated_completion else None
        )
        
    except Exception as e:
        logger.error(f"Failed to get migration metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/sync-operations")
async def get_sync_operations(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[SyncStatus] = None,
    _: User = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get recent sync operations."""
    try:
        sync_service = await get_sync_service()
        
        # In production, this would query from database
        # For now, return mock data
        operations = []
        
        # Generate some sample operations
        statuses = [SyncStatus.COMPLETED, SyncStatus.IN_PROGRESS, SyncStatus.FAILED, SyncStatus.CONFLICT]
        for i in range(min(limit, 20)):
            op_status = status or statuses[i % len(statuses)]
            operations.append({
                "id": f"op_{i}",
                "entityType": "customer" if i % 2 == 0 else "order",
                "entityId": f"entity_{i}",
                "direction": "bidirectional",
                "status": op_status.value,
                "createdAt": (datetime.utcnow() - timedelta(minutes=i * 5)).isoformat(),
                "completedAt": (datetime.utcnow() - timedelta(minutes=i * 5 - 2)).isoformat() if op_status == SyncStatus.COMPLETED else None,
                "errorMessage": "Connection timeout" if op_status == SyncStatus.FAILED else None,
                "retryCount": 1 if op_status == SyncStatus.FAILED else 0
            })
            
        return operations
        
    except Exception as e:
        logger.error(f"Failed to get sync operations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve operations")


@router.get("/conflicts")
async def get_conflicts(
    limit: int = Query(100, ge=1, le=500),
    _: User = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get unresolved conflicts."""
    try:
        sync_service = await get_sync_service()
        conflicts = await sync_service.get_conflicts(limit)
        
        # Enhance with customer names (in production)
        result = []
        for conflict in conflicts:
            conflict_dict = conflict.dict()
            # Add mock customer name
            conflict_dict["customerName"] = f"Customer {conflict.entity_id}"
            conflict_dict["conflictType"] = "data_mismatch"
            result.append(conflict_dict)
            
        return result
        
    except Exception as e:
        logger.error(f"Failed to get conflicts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conflicts")


@router.post("/select-customers", response_model=CustomerSelectionResponse)
async def select_customers(
    request: CustomerSelectionRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
) -> CustomerSelectionResponse:
    """Select customers for pilot program based on criteria."""
    try:
        # Build query
        query = select(Customer).where(Customer.is_active == True)
        
        # Apply filters
        if request.region:
            query = query.where(Customer.address.contains(request.region))
            
        if request.customerType:
            query = query.where(Customer.customer_type == request.customerType)
            
        # Execute query
        result = await db.execute(query)
        customers = result.scalars().all()
        
        # Apply order count filter if specified
        if request.minOrderCount:
            # In production, would join with orders table
            # For now, filter based on mock data
            customers = [c for c in customers if c.total_orders >= request.minOrderCount]
            
        # Calculate selection
        total_count = len(customers)
        select_count = int(total_count * request.percentage / 100)
        
        # Select customers
        import random
        random.seed(42)  # Consistent selection
        selected = random.sample(customers, min(select_count, total_count))
        customer_ids = [c.id for c in selected]
        
        return CustomerSelectionResponse(
            customerIds=customer_ids,
            count=len(customer_ids)
        )
        
    except Exception as e:
        logger.error(f"Failed to select customers: {e}")
        raise HTTPException(status_code=500, detail="Failed to select customers")


@router.post("/start")
async def start_migration(
    request: MigrationStartRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Start migration for selected customers."""
    try:
        sync_service = await get_sync_service()
        feature_service = await get_feature_flag_service()
        
        # Process customers in batches
        for i in range(0, len(request.customerIds), request.batchSize):
            batch = request.customerIds[i:i + request.batchSize]
            
            for customer_id in batch:
                # Add to pilot program
                await feature_service.add_pilot_customer(customer_id)
                
                # Update database
                await db.execute(
                    Customer.__table__.update()
                    .where(Customer.id == customer_id)
                    .values(
                        in_pilot_program=True,
                        pilot_enrolled_at=datetime.utcnow()
                    )
                )
                
                # Queue for sync
                await sync_service.sync_customer(customer_id)
                
        await db.commit()
        
        return {"status": "started", "customerCount": len(request.customerIds)}
        
    except Exception as e:
        logger.error(f"Failed to start migration: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to start migration")


@router.post("/pause")
async def pause_sync(
    _: User = Depends(require_admin)
):
    """Pause synchronization service."""
    try:
        sync_service = await get_sync_service()
        await sync_service.pause_sync()
        return {"status": "paused"}
    except Exception as e:
        logger.error(f"Failed to pause sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause sync")


@router.post("/resume")
async def resume_sync(
    _: User = Depends(require_admin)
):
    """Resume synchronization service."""
    try:
        sync_service = await get_sync_service()
        await sync_service.resume_sync()
        return {"status": "resumed"}
    except Exception as e:
        logger.error(f"Failed to resume sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume sync")


@router.post("/rollback")
async def rollback_migration(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Rollback all migrations."""
    try:
        feature_service = await get_feature_flag_service()
        
        # Get all pilot customers
        pilot_customers = await feature_service.get_pilot_customers()
        
        # Remove from pilot program
        for customer_id in pilot_customers:
            await feature_service.remove_pilot_customer(customer_id)
            
        # Update database
        await db.execute(
            Customer.__table__.update()
            .where(Customer.in_pilot_program == True)
            .values(
                in_pilot_program=False,
                pilot_enrolled_at=None
            )
        )
        await db.commit()
        
        return {"status": "rolled_back", "customerCount": len(pilot_customers)}
        
    except Exception as e:
        logger.error(f"Failed to rollback migration: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to rollback")


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    request: ConflictResolutionRequest,
    _: User = Depends(require_admin)
):
    """Resolve a sync conflict."""
    try:
        sync_service = await get_sync_service()
        success = await sync_service.resolve_conflict(
            conflict_id,
            request.resolution,
            request.resolvedData
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Conflict not found")
            
        return {"status": "resolved", "conflictId": conflict_id}
        
    except Exception as e:
        logger.error(f"Failed to resolve conflict: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve conflict")


@router.get("/feature-flags")
async def get_feature_flags(
    _: User = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get all feature flags."""
    try:
        feature_service = await get_feature_flag_service()
        flags = await feature_service.get_all_flags()
        
        # Convert to response format
        result = []
        for name, flag in flags.items():
            flag_dict = flag.dict()
            # Add enabled customer count
            if flag.type == "customer_list":
                flag_dict["enabledCustomers"] = len(flag.enabled_customers)
            result.append(flag_dict)
            
        return result
        
    except Exception as e:
        logger.error(f"Failed to get feature flags: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve feature flags")


@router.put("/feature-flags/{flag_name}")
async def update_feature_flag(
    flag_name: str,
    request: FeatureFlagUpdateRequest,
    _: User = Depends(require_admin)
):
    """Update a feature flag."""
    try:
        feature_service = await get_feature_flag_service()
        flag = await feature_service.get_flag(flag_name)
        
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
            
        # Update flag
        if request.status:
            flag.status = request.status
        if request.percentage is not None:
            flag.percentage = request.percentage
        if request.enabledCustomers is not None:
            flag.enabled_customers = set(request.enabledCustomers)
            
        success = await feature_service.update_flag(flag_name, flag)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update flag")
            
        return {"status": "updated", "flagName": flag_name}
        
    except Exception as e:
        logger.error(f"Failed to update feature flag: {e}")
        raise HTTPException(status_code=500, detail="Failed to update feature flag")