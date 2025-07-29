"""
Database model for sync operations.

Provides persistent storage for dual-write sync operations
with full audit trail and transaction support.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, DateTime, Integer, JSON, Enum, Boolean,
    Index, UniqueConstraint, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SyncDirection(str, PyEnum):
    """Sync direction."""
    TO_LEGACY = "to_legacy"
    FROM_LEGACY = "from_legacy"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, PyEnum):
    """Sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"
    RETRY = "retry"
    CANCELLED = "cancelled"


class ConflictResolution(str, PyEnum):
    """Conflict resolution strategies."""
    NEWEST_WINS = "newest_wins"
    LEGACY_WINS = "legacy_wins"
    NEW_SYSTEM_WINS = "new_system_wins"
    MANUAL = "manual"
    AUTO_MERGED = "auto_merged"


class EntityType(str, PyEnum):
    """Supported entity types for sync."""
    CUSTOMER = "customer"
    ORDER = "order"
    DELIVERY = "delivery"
    PRODUCT = "product"
    DRIVER = "driver"


class SyncOperation(Base):
    """Sync operation record for audit trail and retry management."""
    __tablename__ = "sync_operations"
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Entity information
    entity_type = Column(Enum(EntityType), nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    entity_version = Column(Integer, default=1)
    
    # Sync configuration
    direction = Column(Enum(SyncDirection), nullable=False)
    priority = Column(Integer, default=0)  # Higher priority processed first
    
    # Status tracking
    status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.PENDING, index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Data storage
    data = Column(JSON, nullable=False)  # Current system data
    legacy_data = Column(JSON)  # Legacy system data (for conflicts)
    original_data = Column(JSON)  # Original data before any modifications
    resolved_data = Column(JSON)  # Resolved data after conflict resolution
    
    # Conflict handling
    conflict_detected = Column(Boolean, default=False)
    conflict_resolution = Column(Enum(ConflictResolution))
    conflict_details = Column(JSON)
    resolved_by = Column(Integer, ForeignKey("users.id"))
    resolved_at = Column(DateTime)
    
    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSON)
    last_error_at = Column(DateTime)
    
    # Transaction support
    transaction_id = Column(String, index=True)  # Groups related operations
    depends_on = Column(String)  # ID of operation this depends on
    batch_id = Column(String, index=True)  # For batch operations
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    next_retry_at = Column(DateTime)
    
    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"))
    updated_by = Column(Integer, ForeignKey("users.id"))
    
    # Performance tracking
    sync_duration_ms = Column(Integer)
    data_size_bytes = Column(Integer)
    
    # Relationships
    resolver = relationship("User", foreign_keys=[resolved_by])
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_sync_operations_status_priority", "status", "priority"),
        Index("idx_sync_operations_entity", "entity_type", "entity_id"),
        Index("idx_sync_operations_transaction", "transaction_id"),
        Index("idx_sync_operations_batch", "batch_id"),
        Index("idx_sync_operations_retry", "status", "next_retry_at"),
        UniqueConstraint("entity_type", "entity_id", "transaction_id", name="uq_entity_transaction"),
    )
    
    def __repr__(self):
        return f"<SyncOperation(id={self.id}, entity={self.entity_type}:{self.entity_id}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "entity_type": self.entity_type.value if self.entity_type else None,
            "entity_id": self.entity_id,
            "entity_version": self.entity_version,
            "direction": self.direction.value if self.direction else None,
            "priority": self.priority,
            "status": self.status.value if self.status else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "data": self.data,
            "legacy_data": self.legacy_data,
            "original_data": self.original_data,
            "resolved_data": self.resolved_data,
            "conflict_detected": self.conflict_detected,
            "conflict_resolution": self.conflict_resolution.value if self.conflict_resolution else None,
            "conflict_details": self.conflict_details,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "transaction_id": self.transaction_id,
            "depends_on": self.depends_on,
            "batch_id": self.batch_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "sync_duration_ms": self.sync_duration_ms,
            "data_size_bytes": self.data_size_bytes
        }


class SyncTransaction(Base):
    """Groups related sync operations into atomic transactions."""
    __tablename__ = "sync_transactions"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Transaction status
    status = Column(Enum(SyncStatus), nullable=False, default=SyncStatus.PENDING)
    operations_count = Column(Integer, default=0)
    completed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Transaction options
    atomic = Column(Boolean, default=True)  # All or nothing
    stop_on_error = Column(Boolean, default=True)
    timeout_seconds = Column(Integer, default=300)  # 5 minutes default
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<SyncTransaction(id={self.id}, name={self.name}, status={self.status})>"