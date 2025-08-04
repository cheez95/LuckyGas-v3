"""
Database models for feature flags with full audit trail.

Provides persistent storage for feature flags, customer assignments,
and complete audit history of all changes.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FeatureFlagType(str, PyEnum):
    """Types of feature flags."""

    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    VARIANT = "variant"
    CUSTOMER_LIST = "customer_list"


class FeatureFlagStatus(str, PyEnum):
    """Feature flag status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SCHEDULED = "scheduled"
    ARCHIVED = "archived"


class AuditAction(str, PyEnum):
    """Audit action types."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    CUSTOMER_ADDED = "customer_added"
    CUSTOMER_REMOVED = "customer_removed"
    PERCENTAGE_CHANGED = "percentage_changed"
    VARIANT_CHANGED = "variant_changed"
    SCHEDULED = "scheduled"


# Association tables
feature_flag_enabled_customers = Table(
    "feature_flag_enabled_customers",
    Base.metadata,
    Column("feature_flag_id", String, ForeignKey("feature_flags.id")),
    Column("customer_id", Integer, ForeignKey("customers.id")),
    Column("enabled_at", DateTime, server_default=func.now()),
    Column("enabled_by", Integer, ForeignKey("users.id")),
    UniqueConstraint("feature_flag_id", "customer_id", name="uq_flag_customer_enabled"),
)

feature_flag_disabled_customers = Table(
    "feature_flag_disabled_customers",
    Base.metadata,
    Column("feature_flag_id", String, ForeignKey("feature_flags.id")),
    Column("customer_id", Integer, ForeignKey("customers.id")),
    Column("disabled_at", DateTime, server_default=func.now()),
    Column("disabled_by", Integer, ForeignKey("users.id")),
    UniqueConstraint(
        "feature_flag_id", "customer_id", name="uq_flag_customer_disabled"
    ),
)


class FeatureFlag(Base):
    """Feature flag configuration with persistence."""

    __tablename__ = "feature_flags"

    # Primary key
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)

    # Basic configuration
    description = Column(Text, nullable=False)
    type = Column(Enum(FeatureFlagType), nullable=False)
    status = Column(
        Enum(FeatureFlagStatus), nullable=False, default=FeatureFlagStatus.INACTIVE
    )

    # Boolean flag
    enabled = Column(Boolean, default=False)

    # Percentage rollout
    percentage = Column(Float, default=0.0)

    # Scheduling
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Metadata
    tags = Column(JSON, default=list)
    config = Column(JSON, default=dict)  # Additional configuration

    # Audit fields
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_by = Column(Integer, ForeignKey("users.id"))
    updated_by = Column(Integer, ForeignKey("users.id"))

    # Statistics
    evaluation_count = Column(Integer, default=0)
    last_evaluated_at = Column(DateTime)

    # Relationships
    enabled_customers = relationship(
        "Customer",
        secondary=feature_flag_enabled_customers,
        backref="enabled_feature_flags",
    )

    disabled_customers = relationship(
        "Customer",
        secondary=feature_flag_disabled_customers,
        backref="disabled_feature_flags",
    )

    variants = relationship(
        "FeatureFlagVariant",
        back_populates="feature_flag",
        cascade="all, delete-orphan",
    )
    audit_logs = relationship(
        "FeatureFlagAudit", back_populates="feature_flag", cascade="all, delete-orphan"
    )

    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

    # Indexes
    __table_args__ = (
        Index("idx_feature_flags_status", "status"),
        Index("idx_feature_flags_type", "type"),
        Index("idx_feature_flags_schedule", "start_date", "end_date"),
    )

    def __repr__(self):
        return (
            f"<FeatureFlag(name={self.name}, type={self.type}, status={self.status})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value if self.type else None,
            "status": self.status.value if self.status else None,
            "enabled": self.enabled,
            "percentage": self.percentage,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "tags": self.tags or [],
            "config": self.config or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "evaluation_count": self.evaluation_count,
            "last_evaluated_at": (
                self.last_evaluated_at.isoformat() if self.last_evaluated_at else None
            ),
            "enabled_customers_count": (
                len(self.enabled_customers) if self.enabled_customers else 0
            ),
            "disabled_customers_count": (
                len(self.disabled_customers) if self.disabled_customers else 0
            ),
            "variants": [v.to_dict() for v in self.variants] if self.variants else [],
        }


class FeatureFlagVariant(Base):
    """A/B test variants for feature flags."""

    __tablename__ = "feature_flag_variants"

    id = Column(String, primary_key=True)
    feature_flag_id = Column(String, ForeignKey("feature_flags.id"), nullable=False)

    name = Column(String, nullable=False)
    percentage = Column(Float, nullable=False)
    config = Column(JSON, default=dict)
    is_default = Column(Boolean, default=False)

    # Statistics
    assignment_count = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    feature_flag = relationship("FeatureFlag", back_populates="variants")

    # Indexes
    __table_args__ = (
        UniqueConstraint("feature_flag_id", "name", name="uq_flag_variant_name"),
        Index("idx_variant_flag", "feature_flag_id"),
    )

    def __repr__(self):
        return f"<FeatureFlagVariant(name={self.name}, percentage={self.percentage})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "percentage": self.percentage,
            "config": self.config or {},
            "is_default": self.is_default,
            "assignment_count": self.assignment_count,
            "conversion_count": self.conversion_count,
        }


class FeatureFlagAudit(Base):
    """Audit log for feature flag changes."""

    __tablename__ = "feature_flag_audits"

    id = Column(String, primary_key=True)
    feature_flag_id = Column(String, ForeignKey("feature_flags.id"), nullable=False)

    # Audit information
    action = Column(Enum(AuditAction), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, nullable=False, server_default=func.now())

    # Change details
    old_value = Column(JSON)
    new_value = Column(JSON)
    details = Column(JSON)  # Additional context

    # Request context
    ip_address = Column(String)
    user_agent = Column(String)
    request_id = Column(String)

    # Relationships
    feature_flag = relationship("FeatureFlag", back_populates="audit_logs")
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_audit_flag_timestamp", "feature_flag_id", "timestamp"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
    )

    def __repr__(self):
        return f"<FeatureFlagAudit(flag_id={self.feature_flag_id}, action={self.action}, timestamp={self.timestamp})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "feature_flag_id": self.feature_flag_id,
            "action": self.action.value if self.action else None,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
        }


class FeatureFlagEvaluation(Base):
    """Records feature flag evaluations for analytics."""

    __tablename__ = "feature_flag_evaluations"

    id = Column(String, primary_key=True)
    feature_flag_id = Column(
        String, ForeignKey("feature_flags.id"), nullable=False, index=True
    )

    # Evaluation context
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    # Result
    enabled = Column(Boolean, nullable=False)
    variant = Column(String)
    reason = Column(String)  # Why it was enabled/disabled

    # Context
    attributes = Column(JSON)  # Additional attributes used in evaluation

    # Performance
    evaluation_time_ms = Column(Float)

    # Indexes
    __table_args__ = (
        Index("idx_evaluation_flag_time", "feature_flag_id", "timestamp"),
        Index("idx_evaluation_customer", "customer_id", "timestamp"),
    )

    def __repr__(self):
        return f"<FeatureFlagEvaluation(flag_id={self.feature_flag_id}, customer_id={self.customer_id}, enabled={self.enabled})>"
