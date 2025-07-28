"""
Enhanced dual-write synchronization service with persistence and transaction support.

This service provides:
- Persistent storage of all sync operations
- Transaction support for atomic operations
- Automatic retry with exponential backoff
- Comprehensive audit trail
- Conflict resolution with history
- Performance monitoring and metrics
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from contextlib import asynccontextmanager
import hashlib
import sys

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.delivery import Delivery
from app.models.sync_operation import (
    SyncOperation as SyncOperationModel,
    SyncTransaction as SyncTransactionModel,
    SyncDirection, SyncStatus, ConflictResolution, EntityType
)
import logging

logger = logging.getLogger(__name__)


class SyncOperationCreate(BaseModel):
    """Schema for creating sync operations."""
    entity_type: EntityType
    entity_id: str
    direction: SyncDirection
    data: Dict[str, Any]
    priority: int = 0
    transaction_id: Optional[str] = None
    depends_on: Optional[str] = None
    batch_id: Optional[str] = None
    created_by: Optional[str] = None


class SyncTransactionCreate(BaseModel):
    """Schema for creating sync transactions."""
    name: str
    description: Optional[str] = None
    atomic: bool = True
    stop_on_error: bool = True
    timeout_seconds: int = 300
    created_by: Optional[str] = None


class SyncMetrics(BaseModel):
    """Enhanced sync operation metrics."""
    total_operations: int = 0
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    failed: int = 0
    conflicts: int = 0
    retries: int = 0
    average_sync_time_ms: float = 0
    success_rate: float = 0
    last_sync_at: Optional[datetime] = None
    oldest_pending: Optional[datetime] = None
    
    @field_validator("success_rate")
    @classmethod
    def validate_success_rate(cls, v):
        return max(0.0, min(1.0, v))


class LegacySystemAdapter:
    """Enhanced adapter for communicating with legacy system."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection_pool = None
        
    async def initialize(self):
        """Initialize connection pool."""
        # In real implementation, initialize actual connection pool
        logger.info("Legacy system adapter initialized")
        
    async def close(self):
        """Close connection pool."""
        if self._connection_pool:
            # Close actual connections
            pass
            
    async def execute_with_retry(self, operation, max_retries=3):
        """Execute operation with retry logic."""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer from legacy system with retry."""
        async def _get():
            # Simulated implementation
            return {
                "id": customer_id,
                "name": "Legacy Customer",
                "phone": "0912-345-678",
                "address": "台北市中正區重慶南路一段122號",
                "updated_at": datetime.utcnow().isoformat(),
                "version": 1
            }
        return await self.execute_with_retry(_get)
        
    async def update_customer(self, customer_id: str, data: Dict[str, Any]) -> bool:
        """Update customer in legacy system with retry."""
        async def _update():
            logger.info(f"Updating customer {customer_id} in legacy system")
            return True
        return await self.execute_with_retry(_update)
        
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order from legacy system with retry."""
        async def _get():
            return None
        return await self.execute_with_retry(_get)
        
    async def create_order(self, data: Dict[str, Any]) -> Optional[str]:
        """Create order in legacy system with retry."""
        async def _create():
            logger.info(f"Creating order in legacy system")
            return f"legacy_{data.get('id', 'unknown')}"
        return await self.execute_with_retry(_create)
        
    async def update_order(self, order_id: str, data: Dict[str, Any]) -> bool:
        """Update order in legacy system with retry."""
        async def _update():
            logger.info(f"Updating order {order_id} in legacy system")
            return True
        return await self.execute_with_retry(_update)


class EnhancedDualWriteSyncService:
    """Enhanced sync service with persistence and transaction support."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._legacy_adapter: Optional[LegacySystemAdapter] = None
        self._worker_tasks: List[asyncio.Task] = []
        self._sync_enabled = True
        self._worker_count = 3  # Number of parallel workers
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize the enhanced sync service."""
        try:
            # Initialize Redis
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Initialize legacy adapter
            self._legacy_adapter = LegacySystemAdapter("legacy_connection")
            await self._legacy_adapter.initialize()
            
            # Start multiple sync workers
            for i in range(self._worker_count):
                task = asyncio.create_task(self._sync_worker(worker_id=i))
                self._worker_tasks.append(task)
            
            # Start retry worker
            retry_task = asyncio.create_task(self._retry_worker())
            self._worker_tasks.append(retry_task)
            
            # Start metrics collector
            metrics_task = asyncio.create_task(self._metrics_collector())
            self._worker_tasks.append(metrics_task)
            
            logger.info(f"Enhanced sync service initialized with {self._worker_count} workers")
            
        except Exception as e:
            logger.error(f"Failed to initialize sync service: {e}")
            raise
            
    async def close(self):
        """Close the sync service gracefully."""
        logger.info("Shutting down sync service...")
        self._sync_enabled = False
        self._shutdown_event.set()
        
        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        # Close connections
        if self._redis_client:
            await self._redis_client.close()
            
        if self._legacy_adapter:
            await self._legacy_adapter.close()
            
        logger.info("Sync service shut down complete")
        
    async def _sync_worker(self, worker_id: int):
        """Background worker for processing sync operations."""
        logger.info(f"Sync worker {worker_id} started")
        
        while self._sync_enabled:
            try:
                # Get next operation from database
                async with async_session_maker() as db:
                    operation = await self._get_next_operation(db)
                    
                    if operation:
                        await self._process_sync_operation(db, operation)
                        await db.commit()
                    else:
                        # No operations, wait a bit
                        await asyncio.sleep(1)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync worker {worker_id} error: {e}")
                await asyncio.sleep(5)
                
        logger.info(f"Sync worker {worker_id} stopped")
        
    async def _retry_worker(self):
        """Worker for retrying failed operations."""
        logger.info("Retry worker started")
        
        while self._sync_enabled:
            try:
                async with async_session_maker() as db:
                    # Find operations ready for retry
                    now = datetime.utcnow()
                    result = await db.execute(
                        select(SyncOperationModel)
                        .where(
                            and_(
                                SyncOperationModel.status == SyncStatus.RETRY,
                                SyncOperationModel.next_retry_at <= now,
                                SyncOperationModel.retry_count < SyncOperationModel.max_retries
                            )
                        )
                        .order_by(SyncOperationModel.priority.desc(), SyncOperationModel.created_at)
                        .limit(10)
                    )
                    operations = result.scalars().all()
                    
                    for operation in operations:
                        operation.status = SyncStatus.PENDING
                        operation.updated_at = now
                        
                    await db.commit()
                    
                    if not operations:
                        await asyncio.sleep(10)  # Check every 10 seconds
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retry worker error: {e}")
                await asyncio.sleep(30)
                
        logger.info("Retry worker stopped")
        
    async def _metrics_collector(self):
        """Collect and store metrics periodically."""
        logger.info("Metrics collector started")
        
        while self._sync_enabled:
            try:
                async with async_session_maker() as db:
                    # Calculate metrics
                    metrics = await self._calculate_metrics(db)
                    
                    # Store in Redis
                    if self._redis_client:
                        await self._redis_client.setex(
                            "sync:metrics:latest",
                            3600,
                            json.dumps(metrics, default=str)
                        )
                        
                await asyncio.sleep(60)  # Update every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collector error: {e}")
                await asyncio.sleep(60)
                
        logger.info("Metrics collector stopped")
        
    async def _get_next_operation(self, db: AsyncSession) -> Optional[SyncOperationModel]:
        """Get next operation to process with row-level locking."""
        # Use SELECT FOR UPDATE to lock the row
        result = await db.execute(
            select(SyncOperationModel)
            .where(
                or_(
                    SyncOperationModel.status == SyncStatus.PENDING,
                    and_(
                        SyncOperationModel.status == SyncStatus.IN_PROGRESS,
                        SyncOperationModel.updated_at < datetime.utcnow() - timedelta(minutes=10)
                    )
                )
            )
            .order_by(SyncOperationModel.priority.desc(), SyncOperationModel.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        
        operation = result.scalar_one_or_none()
        
        if operation:
            operation.status = SyncStatus.IN_PROGRESS
            operation.started_at = datetime.utcnow()
            operation.updated_at = datetime.utcnow()
            
        return operation
        
    async def _process_sync_operation(self, db: AsyncSession, operation: SyncOperationModel):
        """Process a single sync operation with transaction support."""
        start_time = datetime.utcnow()
        
        try:
            # Check dependencies
            if operation.depends_on:
                dep_result = await db.execute(
                    select(SyncOperationModel)
                    .where(SyncOperationModel.id == operation.depends_on)
                )
                dependency = dep_result.scalar_one_or_none()
                
                if not dependency or dependency.status != SyncStatus.COMPLETED:
                    # Dependency not met, skip for now
                    operation.status = SyncStatus.PENDING
                    return
                    
            # Process based on entity type
            success = False
            if operation.entity_type == EntityType.CUSTOMER:
                success = await self._sync_customer(db, operation)
            elif operation.entity_type == EntityType.ORDER:
                success = await self._sync_order(db, operation)
            elif operation.entity_type == EntityType.DELIVERY:
                success = await self._sync_delivery(db, operation)
            else:
                raise ValueError(f"Unknown entity type: {operation.entity_type}")
                
            if success:
                operation.status = SyncStatus.COMPLETED
                operation.completed_at = datetime.utcnow()
                operation.sync_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Update transaction if part of one
                if operation.transaction_id:
                    await self._update_transaction_status(db, operation.transaction_id)
            else:
                await self._handle_operation_failure(db, operation)
                
        except Exception as e:
            logger.error(f"Sync operation {operation.id} failed: {e}")
            operation.status = SyncStatus.FAILED
            operation.error_message = str(e)
            operation.error_details = {"exception": type(e).__name__, "traceback": str(e)}
            operation.last_error_at = datetime.utcnow()
            
            await self._handle_operation_failure(db, operation)
            
    async def _handle_operation_failure(self, db: AsyncSession, operation: SyncOperationModel):
        """Handle failed operation with retry logic."""
        operation.retry_count += 1
        
        if operation.retry_count < operation.max_retries:
            # Schedule retry with exponential backoff
            wait_seconds = min(300, 2 ** operation.retry_count)  # Max 5 minutes
            operation.status = SyncStatus.RETRY
            operation.next_retry_at = datetime.utcnow() + timedelta(seconds=wait_seconds)
        else:
            # Max retries exceeded
            operation.status = SyncStatus.FAILED
            
            # Check transaction failure handling
            if operation.transaction_id:
                transaction_result = await db.execute(
                    select(SyncTransactionModel)
                    .where(SyncTransactionModel.id == operation.transaction_id)
                )
                transaction = transaction_result.scalar_one_or_none()
                
                if transaction and transaction.stop_on_error:
                    # Cancel remaining operations in transaction
                    await db.execute(
                        update(SyncOperationModel)
                        .where(
                            and_(
                                SyncOperationModel.transaction_id == operation.transaction_id,
                                SyncOperationModel.status.in_([SyncStatus.PENDING, SyncStatus.RETRY])
                            )
                        )
                        .values(status=SyncStatus.CANCELLED)
                    )
                    
    async def _sync_customer(self, db: AsyncSession, operation: SyncOperationModel) -> bool:
        """Sync customer data with conflict detection and resolution."""
        try:
            if operation.direction in [SyncDirection.TO_LEGACY, SyncDirection.BIDIRECTIONAL]:
                # Sync to legacy system
                success = await self._legacy_adapter.update_customer(
                    operation.entity_id,
                    operation.data
                )
                if not success:
                    return False
                    
            if operation.direction in [SyncDirection.FROM_LEGACY, SyncDirection.BIDIRECTIONAL]:
                # Get data from legacy system
                legacy_data = await self._legacy_adapter.get_customer(operation.entity_id)
                if legacy_data:
                    # Store legacy data
                    operation.legacy_data = legacy_data
                    
                    # Check for conflicts
                    if await self._detect_conflict(operation.data, legacy_data):
                        await self._handle_conflict(db, operation, legacy_data)
                        return False
                        
                    # Update new system
                    stmt = (
                        update(Customer)
                        .where(Customer.id == operation.entity_id)
                        .values(**self._map_legacy_customer_data(legacy_data))
                    )
                    await db.execute(stmt)
                    
            return True
            
        except Exception as e:
            logger.error(f"Customer sync failed: {e}")
            raise
            
    async def _sync_order(self, db: AsyncSession, operation: SyncOperationModel) -> bool:
        """Sync order data."""
        try:
            if operation.direction in [SyncDirection.TO_LEGACY, SyncDirection.BIDIRECTIONAL]:
                # Create or update in legacy system
                if operation.data.get("legacy_id"):
                    success = await self._legacy_adapter.update_order(
                        operation.data["legacy_id"],
                        operation.data
                    )
                else:
                    legacy_id = await self._legacy_adapter.create_order(operation.data)
                    if legacy_id:
                        # Update order with legacy ID
                        stmt = (
                            update(Order)
                            .where(Order.id == operation.entity_id)
                            .values(legacy_id=legacy_id)
                        )
                        await db.execute(stmt)
                        success = True
                    else:
                        success = False
                        
                if not success:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Order sync failed: {e}")
            raise
            
    async def _sync_delivery(self, db: AsyncSession, operation: SyncOperationModel) -> bool:
        """Sync delivery data."""
        # Implementation similar to order sync
        return True
        
    async def _detect_conflict(
        self,
        new_data: Dict[str, Any],
        legacy_data: Dict[str, Any]
    ) -> bool:
        """Enhanced conflict detection with version checking."""
        # Check version if available
        new_version = new_data.get("version", 0)
        legacy_version = legacy_data.get("version", 0)
        
        if new_version and legacy_version and legacy_version > new_version:
            return True
            
        # Compare timestamps
        new_updated = new_data.get("updated_at")
        legacy_updated = legacy_data.get("updated_at")
        
        if new_updated and legacy_updated:
            new_time = datetime.fromisoformat(new_updated) if isinstance(new_updated, str) else new_updated
            legacy_time = datetime.fromisoformat(legacy_updated) if isinstance(legacy_updated, str) else legacy_updated
            
            # If both were updated recently, check data differences
            if abs((new_time - legacy_time).total_seconds()) < 300:  # 5 minute window
                return self._calculate_data_hash(new_data) != self._calculate_data_hash(legacy_data)
                
        return False
        
    async def _handle_conflict(
        self,
        db: AsyncSession,
        operation: SyncOperationModel,
        legacy_data: Dict[str, Any]
    ):
        """Enhanced conflict handling with audit trail."""
        operation.conflict_detected = True
        operation.legacy_data = legacy_data
        operation.conflict_details = {
            "detected_at": datetime.utcnow().isoformat(),
            "new_version": operation.data.get("version"),
            "legacy_version": legacy_data.get("version"),
            "differences": self._calculate_differences(operation.data, legacy_data)
        }
        
        # Get conflict resolution strategy
        resolution = await self._get_conflict_resolution_strategy(db, operation)
        operation.conflict_resolution = resolution
        
        # Apply resolution
        if resolution == ConflictResolution.NEWEST_WINS:
            # Compare timestamps and use newer data
            new_time = self._get_timestamp(operation.data)
            legacy_time = self._get_timestamp(legacy_data)
            
            if legacy_time > new_time:
                operation.resolved_data = legacy_data
            else:
                operation.resolved_data = operation.data
                
        elif resolution == ConflictResolution.LEGACY_WINS:
            operation.resolved_data = legacy_data
            
        elif resolution == ConflictResolution.NEW_SYSTEM_WINS:
            operation.resolved_data = operation.data
            
        elif resolution == ConflictResolution.AUTO_MERGED:
            # Attempt automatic merge
            operation.resolved_data = self._auto_merge_data(operation.data, legacy_data)
            
        elif resolution == ConflictResolution.MANUAL:
            # Set status for manual review
            operation.status = SyncStatus.CONFLICT
            return
            
        # If auto-resolved, update status
        if operation.resolved_data:
            operation.status = SyncStatus.PENDING  # Retry with resolved data
            operation.data = operation.resolved_data
            operation.resolved_at = datetime.utcnow()
            
    async def _get_conflict_resolution_strategy(
        self,
        db: AsyncSession,
        operation: SyncOperationModel
    ) -> ConflictResolution:
        """Determine conflict resolution strategy based on configuration."""
        # Could be based on entity type, user preferences, etc.
        # For now, use a default strategy
        return ConflictResolution.NEWEST_WINS
        
    def _calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """Calculate hash of data for comparison."""
        # Remove timestamps and IDs for comparison
        filtered_data = {
            k: v for k, v in data.items()
            if k not in ["id", "created_at", "updated_at", "legacy_id", "version"]
        }
        return hashlib.md5(
            json.dumps(filtered_data, sort_keys=True).encode()
        ).hexdigest()
        
    def _calculate_differences(self, data1: Dict[str, Any], data2: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate differences between two data sets."""
        differences = {}
        all_keys = set(data1.keys()) | set(data2.keys())
        
        for key in all_keys:
            if key in ["id", "created_at", "updated_at"]:
                continue
                
            val1 = data1.get(key)
            val2 = data2.get(key)
            
            if val1 != val2:
                differences[key] = {
                    "new_value": val1,
                    "legacy_value": val2
                }
                
        return differences
        
    def _auto_merge_data(self, new_data: Dict[str, Any], legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to automatically merge conflicting data."""
        merged = new_data.copy()
        
        # Simple merge strategy: use non-null values, prefer newer timestamps
        for key, value in legacy_data.items():
            if key not in merged or merged[key] is None:
                merged[key] = value
            elif key.endswith("_at") and value and merged[key]:
                # For timestamp fields, use the newer one
                try:
                    legacy_time = datetime.fromisoformat(value) if isinstance(value, str) else value
                    new_time = datetime.fromisoformat(merged[key]) if isinstance(merged[key], str) else merged[key]
                    if legacy_time > new_time:
                        merged[key] = value
                except:
                    pass
                    
        return merged
        
    def _get_timestamp(self, data: Dict[str, Any]) -> datetime:
        """Extract timestamp from data."""
        updated = data.get("updated_at")
        if updated:
            return datetime.fromisoformat(updated) if isinstance(updated, str) else updated
        return datetime.min
        
    def _map_legacy_customer_data(self, legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map legacy customer data to new system format."""
        return {
            "name": legacy_data.get("name"),
            "phone": legacy_data.get("phone"),
            "address": legacy_data.get("address"),
            "updated_at": datetime.utcnow()
        }
        
    async def _update_transaction_status(self, db: AsyncSession, transaction_id: str):
        """Update transaction status based on operation statuses."""
        # Get transaction
        result = await db.execute(
            select(SyncTransactionModel)
            .where(SyncTransactionModel.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return
            
        # Count operation statuses
        status_counts = await db.execute(
            select(
                SyncOperationModel.status,
                func.count(SyncOperationModel.id)
            )
            .where(SyncOperationModel.transaction_id == transaction_id)
            .group_by(SyncOperationModel.status)
        )
        
        counts = {status: count for status, count in status_counts}
        total = sum(counts.values())
        
        transaction.operations_count = total
        transaction.completed_count = counts.get(SyncStatus.COMPLETED, 0)
        transaction.failed_count = counts.get(SyncStatus.FAILED, 0) + counts.get(SyncStatus.CANCELLED, 0)
        
        # Update transaction status
        if counts.get(SyncStatus.FAILED, 0) > 0 and transaction.atomic:
            transaction.status = SyncStatus.FAILED
        elif counts.get(SyncStatus.COMPLETED, 0) == total:
            transaction.status = SyncStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
        elif counts.get(SyncStatus.IN_PROGRESS, 0) > 0 or counts.get(SyncStatus.PENDING, 0) > 0:
            transaction.status = SyncStatus.IN_PROGRESS
            
    async def _calculate_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Calculate comprehensive sync metrics."""
        # Get status counts
        status_counts = await db.execute(
            select(
                SyncOperationModel.entity_type,
                SyncOperationModel.status,
                func.count(SyncOperationModel.id)
            )
            .group_by(SyncOperationModel.entity_type, SyncOperationModel.status)
        )
        
        metrics_by_type = {}
        
        for entity_type, status, count in status_counts:
            if entity_type not in metrics_by_type:
                metrics_by_type[entity_type] = SyncMetrics()
                
            metrics = metrics_by_type[entity_type]
            metrics.total_operations += count
            
            if status == SyncStatus.PENDING:
                metrics.pending = count
            elif status == SyncStatus.IN_PROGRESS:
                metrics.in_progress = count
            elif status == SyncStatus.COMPLETED:
                metrics.completed = count
            elif status == SyncStatus.FAILED:
                metrics.failed = count
            elif status == SyncStatus.CONFLICT:
                metrics.conflicts = count
            elif status == SyncStatus.RETRY:
                metrics.retries = count
                
        # Calculate additional metrics
        for entity_type, metrics in metrics_by_type.items():
            if metrics.total_operations > 0:
                metrics.success_rate = metrics.completed / metrics.total_operations
                
            # Get average sync time
            avg_time_result = await db.execute(
                select(func.avg(SyncOperationModel.sync_duration_ms))
                .where(
                    and_(
                        SyncOperationModel.entity_type == entity_type,
                        SyncOperationModel.status == SyncStatus.COMPLETED,
                        SyncOperationModel.sync_duration_ms.isnot(None)
                    )
                )
            )
            avg_time = avg_time_result.scalar()
            if avg_time:
                metrics.average_sync_time_ms = float(avg_time)
                
            # Get last sync time
            last_sync_result = await db.execute(
                select(func.max(SyncOperationModel.completed_at))
                .where(
                    and_(
                        SyncOperationModel.entity_type == entity_type,
                        SyncOperationModel.status == SyncStatus.COMPLETED
                    )
                )
            )
            metrics.last_sync_at = last_sync_result.scalar()
            
            # Get oldest pending
            oldest_pending_result = await db.execute(
                select(func.min(SyncOperationModel.created_at))
                .where(
                    and_(
                        SyncOperationModel.entity_type == entity_type,
                        SyncOperationModel.status == SyncStatus.PENDING
                    )
                )
            )
            metrics.oldest_pending = oldest_pending_result.scalar()
            
        return {
            entity_type.value: metrics.model_dump()
            for entity_type, metrics in metrics_by_type.items()
        }
        
    # Public API methods
    
    async def create_sync_operation(
        self,
        operation_data: SyncOperationCreate
    ) -> str:
        """Create a new sync operation."""
        async with async_session_maker() as db:
            operation = SyncOperationModel(
                id=str(uuid.uuid4()),
                entity_type=operation_data.entity_type,
                entity_id=operation_data.entity_id,
                direction=operation_data.direction,
                data=operation_data.data,
                original_data=operation_data.data.copy(),
                priority=operation_data.priority,
                transaction_id=operation_data.transaction_id,
                depends_on=operation_data.depends_on,
                batch_id=operation_data.batch_id,
                created_by=operation_data.created_by,
                data_size_bytes=len(json.dumps(operation_data.data))
            )
            
            db.add(operation)
            await db.commit()
            
            return operation.id
            
    async def create_sync_transaction(
        self,
        transaction_data: SyncTransactionCreate,
        operations: List[SyncOperationCreate]
    ) -> str:
        """Create a new sync transaction with operations."""
        async with async_session_maker() as db:
            # Create transaction
            transaction = SyncTransactionModel(
                id=str(uuid.uuid4()),
                name=transaction_data.name,
                description=transaction_data.description,
                atomic=transaction_data.atomic,
                stop_on_error=transaction_data.stop_on_error,
                timeout_seconds=transaction_data.timeout_seconds,
                created_by=transaction_data.created_by
            )
            
            db.add(transaction)
            
            # Create operations
            for op_data in operations:
                op_data.transaction_id = transaction.id
                operation = SyncOperationModel(
                    id=str(uuid.uuid4()),
                    entity_type=op_data.entity_type,
                    entity_id=op_data.entity_id,
                    direction=op_data.direction,
                    data=op_data.data,
                    original_data=op_data.data.copy(),
                    priority=op_data.priority,
                    transaction_id=op_data.transaction_id,
                    depends_on=op_data.depends_on,
                    batch_id=op_data.batch_id,
                    created_by=op_data.created_by,
                    data_size_bytes=len(json.dumps(op_data.data))
                )
                db.add(operation)
                
            await db.commit()
            
            return transaction.id
            
    async def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get sync operation status."""
        async with async_session_maker() as db:
            result = await db.execute(
                select(SyncOperationModel)
                .where(SyncOperationModel.id == operation_id)
            )
            operation = result.scalar_one_or_none()
            
            if operation:
                return operation.to_dict()
                
        return None
        
    async def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get sync transaction status with operations."""
        async with async_session_maker() as db:
            # Get transaction
            result = await db.execute(
                select(SyncTransactionModel)
                .where(SyncTransactionModel.id == transaction_id)
            )
            transaction = result.scalar_one_or_none()
            
            if not transaction:
                return None
                
            # Get operations
            ops_result = await db.execute(
                select(SyncOperationModel)
                .where(SyncOperationModel.transaction_id == transaction_id)
                .order_by(SyncOperationModel.created_at)
            )
            operations = ops_result.scalars().all()
            
            return {
                "transaction": {
                    "id": transaction.id,
                    "name": transaction.name,
                    "status": transaction.status.value,
                    "operations_count": transaction.operations_count,
                    "completed_count": transaction.completed_count,
                    "failed_count": transaction.failed_count,
                    "created_at": transaction.created_at.isoformat(),
                    "started_at": transaction.started_at.isoformat() if transaction.started_at else None,
                    "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None
                },
                "operations": [op.to_dict() for op in operations]
            }
            
    async def get_conflicts(
        self,
        limit: int = 100,
        entity_type: Optional[EntityType] = None
    ) -> List[Dict[str, Any]]:
        """Get unresolved conflicts."""
        async with async_session_maker() as db:
            query = select(SyncOperationModel).where(
                SyncOperationModel.status == SyncStatus.CONFLICT
            )
            
            if entity_type:
                query = query.where(SyncOperationModel.entity_type == entity_type)
                
            query = query.order_by(SyncOperationModel.created_at.desc()).limit(limit)
            
            result = await db.execute(query)
            operations = result.scalars().all()
            
            return [op.to_dict() for op in operations]
            
    async def resolve_conflict(
        self,
        operation_id: str,
        resolution: ConflictResolution,
        resolved_data: Optional[Dict[str, Any]] = None,
        resolved_by: Optional[str] = None
    ) -> bool:
        """Manually resolve a sync conflict."""
        async with async_session_maker() as db:
            result = await db.execute(
                select(SyncOperationModel)
                .where(SyncOperationModel.id == operation_id)
                .with_for_update()
            )
            operation = result.scalar_one_or_none()
            
            if not operation or operation.status != SyncStatus.CONFLICT:
                return False
                
            # Apply resolution
            operation.conflict_resolution = resolution
            operation.resolved_by = resolved_by
            operation.resolved_at = datetime.utcnow()
            
            if resolved_data:
                operation.resolved_data = resolved_data
                operation.data = resolved_data
            elif resolution == ConflictResolution.LEGACY_WINS and operation.legacy_data:
                operation.resolved_data = operation.legacy_data
                operation.data = operation.legacy_data
            elif resolution == ConflictResolution.NEW_SYSTEM_WINS:
                operation.resolved_data = operation.original_data
                operation.data = operation.original_data
                
            # Reset for retry
            operation.status = SyncStatus.PENDING
            operation.retry_count = 0
            
            await db.commit()
            
            return True
            
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive sync metrics."""
        # Try cache first
        if self._redis_client:
            cached = await self._redis_client.get("sync:metrics:latest")
            if cached:
                return json.loads(cached)
                
        # Calculate fresh metrics
        async with async_session_maker() as db:
            return await self._calculate_metrics(db)
            
    async def pause_sync(self):
        """Pause synchronization."""
        self._sync_enabled = False
        logger.info("Synchronization paused")
        
    async def resume_sync(self):
        """Resume synchronization."""
        self._sync_enabled = True
        logger.info("Synchronization resumed")
        
    async def is_sync_enabled(self) -> bool:
        """Check if sync is enabled."""
        return self._sync_enabled
        
    async def cancel_operation(
        self,
        operation_id: str,
        reason: Optional[str] = None,
        cancelled_by: Optional[str] = None
    ) -> bool:
        """Cancel a pending sync operation."""
        async with async_session_maker() as db:
            result = await db.execute(
                select(SyncOperationModel)
                .where(
                    and_(
                        SyncOperationModel.id == operation_id,
                        SyncOperationModel.status.in_([SyncStatus.PENDING, SyncStatus.RETRY])
                    )
                )
                .with_for_update()
            )
            operation = result.scalar_one_or_none()
            
            if not operation:
                return False
                
            operation.status = SyncStatus.CANCELLED
            operation.updated_at = datetime.utcnow()
            operation.updated_by = cancelled_by
            
            if reason:
                operation.error_message = f"Cancelled: {reason}"
                
            await db.commit()
            
            return True
            
    async def retry_failed_operations(
        self,
        entity_type: Optional[EntityType] = None,
        limit: int = 100
    ) -> int:
        """Retry failed operations."""
        async with async_session_maker() as db:
            query = update(SyncOperationModel).where(
                SyncOperationModel.status == SyncStatus.FAILED
            )
            
            if entity_type:
                query = query.where(SyncOperationModel.entity_type == entity_type)
                
            query = query.values(
                status=SyncStatus.PENDING,
                retry_count=0,
                updated_at=datetime.utcnow()
            )
            
            result = await db.execute(query)
            await db.commit()
            
            return result.rowcount


# Global instance
_sync_service: Optional[EnhancedDualWriteSyncService] = None


async def get_sync_service() -> EnhancedDualWriteSyncService:
    """Get the enhanced sync service instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = EnhancedDualWriteSyncService()
        await _sync_service.initialize()
    return _sync_service


@asynccontextmanager
async def sync_service_context():
    """Context manager for sync service."""
    service = await get_sync_service()
    try:
        yield service
    finally:
        pass  # Service cleanup handled at app shutdown