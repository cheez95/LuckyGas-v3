"""Banking integration models for payment processing."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class PaymentBatchStatus(str, enum.Enum):
    """Payment batch processing status."""

    DRAFT = "draft"
    GENERATED = "generated"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    RECONCILED = "reconciled"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReconciliationStatus(str, enum.Enum):
    """Reconciliation matching status."""

    PENDING = "pending"
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    MANUAL_REVIEW = "manual_review"
    RESOLVED = "resolved"


class TransactionStatus(str, enum.Enum):
    """Individual transaction status."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    REFUNDED = "refunded"


class PaymentBatch(Base):
    """Tracks payment file uploads to banks."""

    __tablename__ = "payment_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(50), unique=True, nullable=False, index=True)
    bank_code = Column(String(10), nullable=False, index=True)

    # File information
    file_name = Column(String(255), nullable=False)
    file_content = Column(Text)  # Store generated file content
    file_format = Column(String(20), nullable=False)  # fixed_width, csv

    # Batch details
    total_transactions = Column(Integer, default=0)
    total_amount = Column(Numeric(10, 2), default=0)
    processing_date = Column(DateTime, nullable=False)

    # Status tracking
    status = Column(
        SQLEnum(PaymentBatchStatus),
        default=PaymentBatchStatus.DRAFT,
        nullable=False,
        index=True,
    )
    generated_at = Column(DateTime)
    uploaded_at = Column(DateTime)
    reconciled_at = Column(DateTime)

    # SFTP tracking
    sftp_upload_path = Column(String(500))
    sftp_download_path = Column(String(500))
    reconciliation_file_name = Column(String(255))

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Audit fields
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transactions = relationship("PaymentTransaction", back_populates="batch")
    reconciliation_logs = relationship("ReconciliationLog", back_populates="batch")

    # Indexes
    __table_args__ = (
        Index("idx_payment_batch_date_bank", "processing_date", "bank_code"),
        Index("idx_payment_batch_status_date", "status", "processing_date"),
    )


class PaymentTransaction(Base):
    """Individual payment transactions within a batch."""

    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(
        Integer, ForeignKey("payment_batches.id"), nullable=False, index=True
    )

    # Transaction details
    transaction_id = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    invoice_id = Column(Integer, ForeignKey("invoices.id"), index=True)

    # Payment information
    account_number = Column(String(20), nullable=False)  # Customer bank account
    account_holder = Column(String(100), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)

    # Status tracking
    status = Column(
        SQLEnum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
        index=True,
    )
    bank_reference = Column(String(50))  # Bank's reference number
    bank_response_code = Column(String(10))
    bank_response_message = Column(Text)

    # Processing dates
    scheduled_date = Column(DateTime, nullable=False)
    processed_date = Column(DateTime)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    batch = relationship("PaymentBatch", back_populates="transactions")
    customer = relationship("Customer")
    invoice = relationship("Invoice")

    # Indexes
    __table_args__ = (
        Index("idx_payment_trans_customer_date", "customer_id", "scheduled_date"),
        Index("idx_payment_trans_status_date", "status", "scheduled_date"),
    )


class ReconciliationLog(Base):
    """Tracks reconciliation file processing and matching results."""

    __tablename__ = "reconciliation_logs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(
        Integer, ForeignKey("payment_batches.id"), nullable=False, index=True
    )

    # File information
    file_name = Column(String(255), nullable=False)
    file_received_at = Column(DateTime, nullable=False)
    file_content = Column(Text)  # Store raw file content for audit

    # Processing statistics
    total_records = Column(Integer, default=0)
    matched_records = Column(Integer, default=0)
    unmatched_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)

    # Status
    status = Column(
        SQLEnum(ReconciliationStatus),
        default=ReconciliationStatus.PENDING,
        nullable=False,
        index=True,
    )
    processed_at = Column(DateTime)

    # Error tracking
    error_details = Column(Text)
    manual_review_notes = Column(Text)

    # Audit fields
    processed_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    batch = relationship("PaymentBatch", back_populates="reconciliation_logs")
    processed_by_user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_reconciliation_status_date", "status", "file_received_at"),
    )


class BankConfiguration(Base):
    """Stores bank - specific configuration for SFTP and file formats."""

    __tablename__ = "bank_configurations"

    id = Column(Integer, primary_key=True, index=True)
    bank_code = Column(String(10), unique=True, nullable=False, index=True)
    bank_name = Column(String(100), nullable=False)

    # SFTP Configuration (encrypted in production)
    sftp_host = Column(String(255), nullable=False)
    sftp_port = Column(Integer, default=22)
    sftp_username = Column(String(100), nullable=False)
    sftp_password = Column(String(255), nullable=False)  # Should be encrypted
    sftp_private_key = Column(Text)  # Optional: for key - based auth

    # File paths
    upload_path = Column(String(500), nullable=False)
    download_path = Column(String(500), nullable=False)
    archive_path = Column(String(500))

    # File format configuration
    file_format = Column(String(20), nullable=False)  # fixed_width, csv
    encoding = Column(String(20), default="UTF - 8")  # UTF - 8, Big5
    delimiter = Column(String(5))  # For CSV format

    # File naming patterns
    payment_file_pattern = Column(String(100))  # e.g., "PAY_{YYYYMMDD}_{BATCH}.txt"
    reconciliation_file_pattern = Column(String(100))  # e.g., "REC_{YYYYMMDD}.txt"

    # Processing configuration
    is_active = Column(Boolean, default=True)
    cutoff_time = Column(String(5))  # HH:MM format
    retry_attempts = Column(Integer, default=3)
    retry_delay_minutes = Column(Integer, default=30)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
