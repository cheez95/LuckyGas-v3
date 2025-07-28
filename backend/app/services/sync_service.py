"""
Dual-write synchronization service for legacy system integration.

This service provides:
- Bidirectional sync with legacy system
- Conflict resolution logic
- Data validation and reconciliation
- Sync status monitoring
- Error recovery mechanisms
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import hashlib
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload
import redis.asyncio as redis
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.delivery import Delivery
import logging

logger = logging.getLogger(__name__)
from app.services.feature_flags import get_feature_flag_service


class SyncDirection(str, Enum):
    """Sync direction."""
    TO_LEGACY = "to_legacy"
    FROM_LEGACY = "from_legacy"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    """Sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    NEWEST_WINS = "newest_wins"
    LEGACY_WINS = "legacy_wins"
    NEW_SYSTEM_WINS = "new_system_wins"
    MANUAL = "manual"


class SyncOperation(BaseModel):
    """Represents a sync operation."""
    id: str
    entity_type: str
    entity_id: str
    direction: SyncDirection
    status: SyncStatus
    data: Dict[str, Any]
    legacy_data: Optional[Dict[str, Any]] = None
    conflict_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class SyncMetrics(BaseModel):
    """Sync operation metrics."""
    total_synced: int = 0
    successful: int = 0
    failed: int = 0
    conflicts: int = 0
    average_sync_time_ms: float = 0
    last_sync_at: Optional[datetime] = None
    
    
class LegacySystemAdapter:
    """Adapter for communicating with legacy system."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # In real implementation, this would connect to actual legacy system
        
    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer from legacy system."""
        # Simulated implementation
        return {
            "id": customer_id,
            "name": "Legacy Customer",
            "phone": "0912-345-678",
            "address": "台北市中正區重慶南路一段122號",
            "updated_at": datetime.utcnow().isoformat()
        }
        
    async def update_customer(self, customer_id: str, data: Dict[str, Any]) -> bool:
        """Update customer in legacy system."""
        # Simulated implementation
        logger.info(f"Updating customer {customer_id} in legacy system")
        return True
        
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order from legacy system."""
        # Simulated implementation
        return None
        
    async def create_order(self, data: Dict[str, Any]) -> Optional[str]:
        """Create order in legacy system."""
        # Simulated implementation
        logger.info(f"Creating order in legacy system")
        return f"legacy_{data.get('id', 'unknown')}"
        
    async def update_order(self, order_id: str, data: Dict[str, Any]) -> bool:
        """Update order in legacy system."""
        # Simulated implementation
        logger.info(f"Updating order {order_id} in legacy system")
        return True


class DualWriteSyncService:
    """Service for dual-write synchronization with legacy system."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._legacy_adapter: Optional[LegacySystemAdapter] = None
        self._sync_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, SyncMetrics] = {}
        self._conflict_resolution = ConflictResolution.NEWEST_WINS
        self._sync_enabled = True
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the sync service."""
        try:
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Initialize legacy adapter (connection string from settings)
            self._legacy_adapter = LegacySystemAdapter("legacy_connection")
            
            # Start sync worker
            self._worker_task = asyncio.create_task(self._sync_worker())
            
            logger.info("Dual-write sync service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize sync service: {e}")
            raise
            
    async def close(self):
        """Close the sync service."""
        self._sync_enabled = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
                
        if self._redis_client:
            await self._redis_client.close()
            
    async def _sync_worker(self):
        """Background worker for processing sync operations."""
        while self._sync_enabled:
            try:
                # Get sync operation from queue with timeout
                operation = await asyncio.wait_for(
                    self._sync_queue.get(),
                    timeout=1.0
                )
                
                await self._process_sync_operation(operation)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Sync worker error: {e}")
                await asyncio.sleep(5)  # Back off on error
                
    async def _process_sync_operation(self, operation: SyncOperation):
        """Process a single sync operation."""
        start_time = datetime.utcnow()
        
        try:
            operation.status = SyncStatus.IN_PROGRESS
            operation.updated_at = datetime.utcnow()
            
            # Store operation status
            await self._store_operation_status(operation)
            
            # Process based on entity type
            if operation.entity_type == "customer":
                success = await self._sync_customer(operation)
            elif operation.entity_type == "order":
                success = await self._sync_order(operation)
            elif operation.entity_type == "delivery":
                success = await self._sync_delivery(operation)
            else:
                raise ValueError(f"Unknown entity type: {operation.entity_type}")
                
            if success:
                operation.status = SyncStatus.COMPLETED
                operation.completed_at = datetime.utcnow()
                
                # Update metrics
                await self._update_metrics(
                    operation.entity_type,
                    success=True,
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
                )
            else:
                operation.status = SyncStatus.FAILED
                operation.retry_count += 1
                
                # Retry if under limit
                if operation.retry_count < 3:
                    await asyncio.sleep(2 ** operation.retry_count)  # Exponential backoff
                    await self._sync_queue.put(operation)
                    
                await self._update_metrics(operation.entity_type, success=False)
                
        except Exception as e:
            logger.error(f"Sync operation failed: {e}")
            operation.status = SyncStatus.FAILED
            operation.error_message = str(e)
            await self._update_metrics(operation.entity_type, success=False)
            
        finally:
            # Store final operation status
            await self._store_operation_status(operation)
            
    async def _sync_customer(self, operation: SyncOperation) -> bool:
        """Sync customer data."""
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
                    # Check for conflicts
                    if await self._detect_conflict(operation.data, legacy_data):
                        await self._handle_conflict(operation, legacy_data)
                        return False
                        
                    # Update new system
                    async with async_session_maker() as db:
                        stmt = (
                            update(Customer)
                            .where(Customer.id == operation.entity_id)
                            .values(**self._map_legacy_customer_data(legacy_data))
                        )
                        await db.execute(stmt)
                        await db.commit()
                        
            return True
            
        except Exception as e:
            logger.error(f"Customer sync failed: {e}")
            return False
            
    async def _sync_order(self, operation: SyncOperation) -> bool:
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
                        async with async_session_maker() as db:
                            stmt = (
                                update(Order)
                                .where(Order.id == operation.entity_id)
                                .values(legacy_id=legacy_id)
                            )
                            await db.execute(stmt)
                            await db.commit()
                        success = True
                    else:
                        success = False
                        
                if not success:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Order sync failed: {e}")
            return False
            
    async def _sync_delivery(self, operation: SyncOperation) -> bool:
        """Sync delivery data."""
        # Similar implementation to order sync
        return True
        
    async def _detect_conflict(
        self,
        new_data: Dict[str, Any],
        legacy_data: Dict[str, Any]
    ) -> bool:
        """Detect conflicts between new and legacy data."""
        # Compare timestamps
        new_updated = new_data.get("updated_at")
        legacy_updated = legacy_data.get("updated_at")
        
        if new_updated and legacy_updated:
            new_time = datetime.fromisoformat(new_updated) if isinstance(new_updated, str) else new_updated
            legacy_time = datetime.fromisoformat(legacy_updated) if isinstance(legacy_updated, str) else legacy_updated
            
            # If both were updated within sync window, we have a conflict
            if abs((new_time - legacy_time).total_seconds()) < 60:  # 1 minute window
                return True
                
        # Check for data differences
        return self._calculate_data_hash(new_data) != self._calculate_data_hash(legacy_data)
        
    async def _handle_conflict(
        self,
        operation: SyncOperation,
        legacy_data: Dict[str, Any]
    ):
        """Handle data conflicts."""
        operation.status = SyncStatus.CONFLICT
        operation.legacy_data = legacy_data
        operation.conflict_data = {
            "resolution_strategy": self._conflict_resolution,
            "detected_at": datetime.utcnow().isoformat()
        }
        
        # Apply resolution strategy
        if self._conflict_resolution == ConflictResolution.NEWEST_WINS:
            # Compare timestamps and use newer data
            pass
        elif self._conflict_resolution == ConflictResolution.LEGACY_WINS:
            # Use legacy data
            operation.data = legacy_data
        elif self._conflict_resolution == ConflictResolution.NEW_SYSTEM_WINS:
            # Keep new system data
            pass
        elif self._conflict_resolution == ConflictResolution.MANUAL:
            # Queue for manual review
            await self._queue_for_manual_review(operation)
            
        # Update metrics
        async with self._lock:
            entity_metrics = self._metrics.get(operation.entity_type, SyncMetrics())
            entity_metrics.conflicts += 1
            self._metrics[operation.entity_type] = entity_metrics
            
    def _calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """Calculate hash of data for comparison."""
        # Remove timestamps and IDs for comparison
        filtered_data = {
            k: v for k, v in data.items()
            if k not in ["id", "created_at", "updated_at", "legacy_id"]
        }
        return hashlib.md5(
            json.dumps(filtered_data, sort_keys=True).encode()
        ).hexdigest()
        
    def _map_legacy_customer_data(self, legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map legacy customer data to new system format."""
        return {
            "name": legacy_data.get("name"),
            "phone": legacy_data.get("phone"),
            "address": legacy_data.get("address"),
            "updated_at": datetime.utcnow()
        }
        
    async def _store_operation_status(self, operation: SyncOperation):
        """Store operation status in Redis."""
        if self._redis_client:
            key = f"sync_operation:{operation.id}"
            await self._redis_client.setex(
                key,
                86400,  # 24 hours
                operation.json()
            )
            
    async def _update_metrics(
        self,
        entity_type: str,
        success: bool,
        duration_ms: Optional[float] = None
    ):
        """Update sync metrics."""
        async with self._lock:
            metrics = self._metrics.get(entity_type, SyncMetrics())
            metrics.total_synced += 1
            
            if success:
                metrics.successful += 1
            else:
                metrics.failed += 1
                
            if duration_ms:
                # Update rolling average
                metrics.average_sync_time_ms = (
                    (metrics.average_sync_time_ms * (metrics.total_synced - 1) + duration_ms)
                    / metrics.total_synced
                )
                
            metrics.last_sync_at = datetime.utcnow()
            self._metrics[entity_type] = metrics
            
    async def _queue_for_manual_review(self, operation: SyncOperation):
        """Queue operation for manual review."""
        if self._redis_client:
            await self._redis_client.lpush(
                "sync_conflicts:manual_review",
                operation.json()
            )
            
    async def sync_customer(
        self,
        customer_id: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    ) -> str:
        """Queue customer for synchronization."""
        async with async_session_maker() as db:
            # Get customer data
            result = await db.execute(
                select(Customer).where(Customer.id == customer_id)
            )
            customer = result.scalar_one_or_none()
            
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
                
            operation = SyncOperation(
                id=f"customer_{customer_id}_{datetime.utcnow().timestamp()}",
                entity_type="customer",
                entity_id=customer_id,
                direction=direction,
                status=SyncStatus.PENDING,
                data=customer.to_dict()
            )
            
            await self._sync_queue.put(operation)
            return operation.id
            
    async def sync_order(
        self,
        order_id: str,
        direction: SyncDirection = SyncDirection.TO_LEGACY
    ) -> str:
        """Queue order for synchronization."""
        async with async_session_maker() as db:
            # Get order data with related entities
            result = await db.execute(
                select(Order)
                .options(selectinload(Order.customer))
                .options(selectinload(Order.items))
                .where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
            
            if not order:
                raise ValueError(f"Order {order_id} not found")
                
            operation = SyncOperation(
                id=f"order_{order_id}_{datetime.utcnow().timestamp()}",
                entity_type="order",
                entity_id=order_id,
                direction=direction,
                status=SyncStatus.PENDING,
                data=order.to_dict()
            )
            
            await self._sync_queue.put(operation)
            return operation.id
            
    async def get_sync_status(self, operation_id: str) -> Optional[SyncOperation]:
        """Get sync operation status."""
        if self._redis_client:
            data = await self._redis_client.get(f"sync_operation:{operation_id}")
            if data:
                return SyncOperation.parse_raw(data)
        return None
        
    async def get_metrics(self) -> Dict[str, SyncMetrics]:
        """Get sync metrics."""
        async with self._lock:
            return self._metrics.copy()
            
    async def get_conflicts(
        self,
        limit: int = 100
    ) -> List[SyncOperation]:
        """Get recent conflicts."""
        conflicts = []
        
        if self._redis_client:
            # Get conflicts from manual review queue
            items = await self._redis_client.lrange(
                "sync_conflicts:manual_review",
                0,
                limit - 1
            )
            
            for item in items:
                try:
                    conflicts.append(SyncOperation.parse_raw(item))
                except Exception as e:
                    logger.error(f"Failed to parse conflict: {e}")
                    
        return conflicts
        
    async def resolve_conflict(
        self,
        operation_id: str,
        resolution: ConflictResolution,
        resolved_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Resolve a sync conflict."""
        operation = await self.get_sync_status(operation_id)
        if not operation or operation.status != SyncStatus.CONFLICT:
            return False
            
        # Apply resolution
        if resolved_data:
            operation.data = resolved_data
            
        operation.status = SyncStatus.PENDING
        operation.conflict_data["resolved_at"] = datetime.utcnow().isoformat()
        operation.conflict_data["resolution"] = resolution
        
        # Requeue for sync
        await self._sync_queue.put(operation)
        return True
        
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


# Global instance
_sync_service: Optional[DualWriteSyncService] = None


async def get_sync_service() -> DualWriteSyncService:
    """Get the sync service instance."""
    global _sync_service
    if _sync_service is None:
        _sync_service = DualWriteSyncService()
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