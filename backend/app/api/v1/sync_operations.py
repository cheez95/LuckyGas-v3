"""
API endpoints for sync operations management.

Provides REST API for monitoring and managing dual-write sync operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.api.deps import get_db, get_current_user, get_current_active_superuser
from app.models.user import User
from app.models.sync_operation import (
    SyncOperation as SyncOperationModel,
    SyncTransaction as SyncTransactionModel,
    SyncDirection, SyncStatus, ConflictResolution, EntityType
)
from app.services.sync_service_enhanced import (
    get_sync_service,
    SyncOperationCreate,
    SyncTransactionCreate
)

router = APIRouter(prefix="/sync", tags=["sync_operations"])


@router.post("/operations", response_model=Dict[str, str])
async def create_sync_operation(
    operation_data: SyncOperationCreate,
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> Dict[str, str]:
    """
    Create a new sync operation.
    
    Requires authentication.
    """
    operation_data.created_by = current_user.id
    operation_id = await service.create_sync_operation(operation_data)
    
    return {
        "operation_id": operation_id,
        "message": "同步操作已創建"
    }


@router.post("/transactions", response_model=Dict[str, str])
async def create_sync_transaction(
    transaction_data: SyncTransactionCreate,
    operations: List[SyncOperationCreate] = Body(..., description="List of operations in transaction"),
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> Dict[str, str]:
    """
    Create a new sync transaction with multiple operations.
    
    All operations will be executed atomically if transaction is configured as atomic.
    """
    if not operations:
        raise HTTPException(
            status_code=400,
            detail="交易必須包含至少一個操作"
        )
        
    transaction_data.created_by = current_user.id
    for op in operations:
        op.created_by = current_user.id
        
    transaction_id = await service.create_sync_transaction(transaction_data, operations)
    
    return {
        "transaction_id": transaction_id,
        "message": f"同步交易已創建，包含 {len(operations)} 個操作"
    }


@router.get("/operations/{operation_id}", response_model=Dict[str, Any])
async def get_operation_status(
    operation_id: str,
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> Dict[str, Any]:
    """
    Get sync operation status and details.
    """
    operation = await service.get_operation_status(operation_id)
    
    if not operation:
        raise HTTPException(
            status_code=404,
            detail="同步操作不存在"
        )
        
    return operation


@router.get("/transactions/{transaction_id}", response_model=Dict[str, Any])
async def get_transaction_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> Dict[str, Any]:
    """
    Get sync transaction status with all operations.
    """
    transaction = await service.get_transaction_status(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="同步交易不存在"
        )
        
    return transaction


@router.get("/conflicts", response_model=List[Dict[str, Any]])
async def get_conflicts(
    limit: int = Query(100, description="Maximum number of conflicts to return"),
    entity_type: Optional[EntityType] = Query(None, description="Filter by entity type"),
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> List[Dict[str, Any]]:
    """
    Get list of unresolved sync conflicts.
    """
    conflicts = await service.get_conflicts(limit=limit, entity_type=entity_type)
    
    return conflicts


@router.post("/conflicts/{operation_id}/resolve", response_model=Dict[str, str])
async def resolve_conflict(
    operation_id: str,
    resolution: ConflictResolution = Body(..., description="Resolution strategy"),
    resolved_data: Optional[Dict[str, Any]] = Body(None, description="Manually resolved data"),
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> Dict[str, str]:
    """
    Manually resolve a sync conflict.
    """
    success = await service.resolve_conflict(
        operation_id=operation_id,
        resolution=resolution,
        resolved_data=resolved_data,
        resolved_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="無法解決衝突，請檢查操作狀態"
        )
        
    return {
        "message": "衝突已解決",
        "resolution": resolution.value
    }


@router.get("/metrics", response_model=Dict[str, Any])
async def get_sync_metrics(
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> Dict[str, Any]:
    """
    Get comprehensive sync metrics by entity type.
    """
    metrics = await service.get_metrics()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics
    }


@router.post("/pause", response_model=Dict[str, str])
async def pause_sync(
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_sync_service)
) -> Dict[str, str]:
    """
    Pause all sync operations.
    
    Requires admin privileges.
    """
    await service.pause_sync()
    
    return {
        "message": "同步已暫停",
        "paused_by": current_user.email
    }


@router.post("/resume", response_model=Dict[str, str])
async def resume_sync(
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_sync_service)
) -> Dict[str, str]:
    """
    Resume sync operations.
    
    Requires admin privileges.
    """
    await service.resume_sync()
    
    return {
        "message": "同步已恢復",
        "resumed_by": current_user.email
    }


@router.get("/status", response_model=Dict[str, Any])
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> Dict[str, Any]:
    """
    Get overall sync service status.
    """
    is_enabled = await service.is_sync_enabled()
    metrics = await service.get_metrics()
    
    # Calculate totals
    total_operations = 0
    total_pending = 0
    total_failed = 0
    
    for entity_metrics in metrics.values():
        total_operations += entity_metrics.get("total_operations", 0)
        total_pending += entity_metrics.get("pending", 0)
        total_failed += entity_metrics.get("failed", 0)
        
    return {
        "enabled": is_enabled,
        "total_operations": total_operations,
        "pending_operations": total_pending,
        "failed_operations": total_failed,
        "metrics_by_entity": metrics
    }


@router.delete("/operations/{operation_id}", response_model=Dict[str, str])
async def cancel_operation(
    operation_id: str,
    reason: Optional[str] = Body(None, description="Cancellation reason"),
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service)
) -> Dict[str, str]:
    """
    Cancel a pending sync operation.
    """
    success = await service.cancel_operation(
        operation_id=operation_id,
        reason=reason,
        cancelled_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="無法取消操作，操作可能已經開始或完成"
        )
        
    return {
        "message": "操作已取消",
        "cancelled_by": current_user.email
    }


@router.post("/retry-failed", response_model=Dict[str, Any])
async def retry_failed_operations(
    entity_type: Optional[EntityType] = Query(None, description="Filter by entity type"),
    limit: int = Query(100, description="Maximum number of operations to retry"),
    current_user: User = Depends(get_current_active_superuser),
    service = Depends(get_sync_service)
) -> Dict[str, Any]:
    """
    Retry all failed operations.
    
    Requires admin privileges.
    """
    count = await service.retry_failed_operations(
        entity_type=entity_type,
        limit=limit
    )
    
    return {
        "message": f"已重試 {count} 個失敗的操作",
        "retried_count": count,
        "entity_type": entity_type.value if entity_type else "all"
    }


@router.get("/operations", response_model=Dict[str, Any])
async def list_operations(
    status: Optional[SyncStatus] = Query(None, description="Filter by status"),
    entity_type: Optional[EntityType] = Query(None, description="Filter by entity type"),
    limit: int = Query(50, description="Maximum number of operations"),
    offset: int = Query(0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    List sync operations with filtering and pagination.
    """
    # Build query
    query = select(SyncOperationModel)
    
    if status:
        query = query.where(SyncOperationModel.status == status)
        
    if entity_type:
        query = query.where(SyncOperationModel.entity_type == entity_type)
        
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar()
    
    # Get operations with pagination
    query = query.order_by(SyncOperationModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    operations = result.scalars().all()
    
    return {
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "operations": [op.to_dict() for op in operations]
    }


@router.get("/health", response_model=Dict[str, Any])
async def get_sync_health(
    current_user: User = Depends(get_current_user),
    service = Depends(get_sync_service),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get sync service health status.
    """
    # Check if service is running
    is_enabled = await service.is_sync_enabled()
    
    # Get recent operation stats
    recent_time = datetime.utcnow() - timedelta(minutes=5)
    
    recent_stats = await db.execute(
        select(
            SyncOperationModel.status,
            func.count(SyncOperationModel.id).label("count")
        )
        .where(SyncOperationModel.created_at >= recent_time)
        .group_by(SyncOperationModel.status)
    )
    
    stats = {status.value: count for status, count in recent_stats}
    
    # Calculate health score
    total_recent = sum(stats.values())
    failed_recent = stats.get(SyncStatus.FAILED.value, 0)
    
    if total_recent == 0:
        health_score = 100
    else:
        success_rate = 1 - (failed_recent / total_recent)
        health_score = int(success_rate * 100)
        
    # Get oldest pending operation
    oldest_pending_result = await db.execute(
        select(func.min(SyncOperationModel.created_at))
        .where(SyncOperationModel.status == SyncStatus.PENDING)
    )
    oldest_pending = oldest_pending_result.scalar()
    
    return {
        "status": "healthy" if health_score >= 80 and is_enabled else "degraded" if health_score >= 50 else "unhealthy",
        "enabled": is_enabled,
        "health_score": health_score,
        "recent_operations": stats,
        "oldest_pending_minutes": int((datetime.utcnow() - oldest_pending).total_seconds() / 60) if oldest_pending else 0
    }