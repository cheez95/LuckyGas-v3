"""Pydantic schemas for banking operations."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class PaymentBatchStatus(str, Enum):
    """Payment batch processing status."""

    DRAFT = "draft"
    GENERATED = "generated"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    RECONCILED = "reconciled"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReconciliationStatus(str, Enum):
    """Reconciliation matching status."""

    PENDING = "pending"
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    MANUAL_REVIEW = "manual_review"
    RESOLVED = "resolved"


class TransactionStatus(str, Enum):
    """Individual transaction status."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"
    REFUNDED = "refunded"


# Bank Configuration Schemas


class BankConfigBase(BaseModel):
    """Base schema for bank configuration."""

    bank_code: str = Field(
        ..., max_length=10, description="Bank code (e.g., CTBC, ESUN)"
    )
    bank_name: str = Field(..., max_length=100, description="Bank name")
    sftp_host: str = Field(..., description="SFTP server hostname")
    sftp_port: int = Field(default=22, description="SFTP server port")
    sftp_username: str = Field(..., description="SFTP username")
    upload_path: str = Field(..., description="Remote upload directory path")
    download_path: str = Field(..., description="Remote download directory path")
    archive_path: Optional[str] = Field(
        None, description="Remote archive directory path"
    )
    file_format: str = Field(
        ..., pattern="^(fixed_width|csv)$", description="File format type"
    )
    encoding: str = Field(
        default="UTF - 8", description="File encoding (UTF - 8 or Big5)"
    )
    delimiter: Optional[str] = Field(None, max_length=5, description="CSV delimiter")
    payment_file_pattern: Optional[str] = Field(
        None, description="Payment file naming pattern"
    )
    reconciliation_file_pattern: Optional[str] = Field(
        None, description="Reconciliation file naming pattern"
    )
    is_active: bool = Field(default=True, description="Configuration active status")
    cutoff_time: Optional[str] = Field(
        None, pattern="^\\d{2}:\\d{2}$", description="Daily cutoff time (HH:MM)"
    )
    retry_attempts: int = Field(
        default=3, ge=0, le=10, description="Number of retry attempts"
    )
    retry_delay_minutes: int = Field(
        default=30, ge=5, le=360, description="Delay between retries in minutes"
    )


class BankConfigCreate(BankConfigBase):
    """Schema for creating bank configuration."""

    sftp_password: str = Field(..., description="SFTP password (will be encrypted)")
    sftp_private_key: Optional[str] = Field(
        None, description="SSH private key for key - based auth"
    )


class BankConfigUpdate(BaseModel):
    """Schema for updating bank configuration."""

    bank_name: Optional[str] = None
    sftp_host: Optional[str] = None
    sftp_port: Optional[int] = None
    sftp_username: Optional[str] = None
    sftp_password: Optional[str] = None
    sftp_private_key: Optional[str] = None
    upload_path: Optional[str] = None
    download_path: Optional[str] = None
    archive_path: Optional[str] = None
    file_format: Optional[str] = None
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    payment_file_pattern: Optional[str] = None
    reconciliation_file_pattern: Optional[str] = None
    is_active: Optional[bool] = None
    cutoff_time: Optional[str] = None
    retry_attempts: Optional[int] = None
    retry_delay_minutes: Optional[int] = None


class BankConfigResponse(BankConfigBase):
    """Schema for bank configuration response."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Payment Batch Schemas


class PaymentBatchCreate(BaseModel):
    """Schema for creating a payment batch."""

    bank_code: str = Field(..., description="Bank code for processing")
    processing_date: datetime = Field(..., description="Date to process payments")
    invoice_ids: Optional[List[int]] = Field(
        None, description="Specific invoice IDs to include"
    )


class PaymentBatchResponse(BaseModel):
    """Schema for payment batch response."""

    id: int
    batch_number: str
    bank_code: str
    file_name: Optional[str]
    file_format: str
    total_transactions: int
    total_amount: float
    processing_date: datetime
    status: PaymentBatchStatus
    generated_at: Optional[datetime]
    uploaded_at: Optional[datetime]
    reconciled_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Payment Transaction Schemas


class PaymentTransactionResponse(BaseModel):
    """Schema for payment transaction response."""

    id: int
    batch_id: int
    transaction_id: str
    customer_id: int
    invoice_id: Optional[int]
    account_number: str
    account_holder: str
    amount: float
    status: TransactionStatus
    bank_reference: Optional[str]
    bank_response_code: Optional[str]
    bank_response_message: Optional[str]
    scheduled_date: datetime
    processed_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Reconciliation Schemas


class ReconciliationLogResponse(BaseModel):
    """Schema for reconciliation log response."""

    id: int
    batch_id: Optional[int]
    file_name: str
    file_received_at: datetime
    total_records: int
    matched_records: int
    unmatched_records: int
    failed_records: int
    status: ReconciliationStatus
    processed_at: Optional[datetime]
    error_details: Optional[str]
    manual_review_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# File Operation Schemas


class GeneratePaymentFileRequest(BaseModel):
    """Request to generate a payment file."""

    batch_id: int = Field(..., description="Payment batch ID")


class GeneratePaymentFileResponse(BaseModel):
    """Response after generating a payment file."""

    success: bool
    file_name: str
    file_size: int
    message: str


class UploadFileRequest(BaseModel):
    """Request to upload a file to bank."""

    batch_id: int = Field(..., description="Payment batch ID")


class UploadFileResponse(BaseModel):
    """Response after uploading a file."""

    success: bool
    uploaded_at: datetime
    remote_path: str
    message: str


class CheckReconciliationResponse(BaseModel):
    """Response for checking reconciliation files."""

    bank_code: str
    new_files: List[str]
    checked_at: datetime


class ProcessReconciliationRequest(BaseModel):
    """Request to process a reconciliation file."""

    bank_code: str = Field(..., description="Bank code")
    file_name: str = Field(..., description="File name to process")


# Report Schemas


class PaymentStatusReport(BaseModel):
    """Detailed payment status report."""

    batch_id: int
    batch_number: str
    bank_code: str
    status: str
    processing_date: str
    total_transactions: int
    total_amount: float
    created_at: str
    uploaded_at: Optional[str]
    reconciled_at: Optional[str]
    status_summary: Dict[str, Dict[str, Any]]
    failed_transactions: List[Dict[str, Any]]
    reconciliation_file: Optional[str]
    error_message: Optional[str]


class PaymentBatchListResponse(BaseModel):
    """Response for listing payment batches."""

    items: List[PaymentBatchResponse]
    total: int
    page: int
    size: int
    pages: int


# Banking Monitor Schemas


class BankingHealthCheck(BaseModel):
    """Banking system health check response."""

    status: str
    timestamp: str
    circuit_breakers: Dict[str, Dict[str, Any]]
    connection_pools: Dict[str, Dict[str, Any]]
    retry_queue_size: int
    checks: List[Dict[str, str]]
    daily_batches: Dict[str, int]
    daily_reconciliations: Dict[str, int]


class TransferHistory(BaseModel):
    """SFTP transfer history entry."""

    file_name: str
    remote_path: str
    success: bool
    transfer_time: float
    checksum: str
    error: Optional[str]
    retry_count: int
    timestamp: str


class PaymentBatchDetail(BaseModel):
    """Detailed payment batch information."""

    batch_id: int
    batch_number: str
    bank_code: str
    status: str
    processing_date: str
    total_transactions: int
    total_amount: float
    created_at: str
    uploaded_at: Optional[str]
    reconciled_at: Optional[str]
    status_summary: Dict[str, Dict[str, Any]]
    failed_transactions: List[Dict[str, Any]]
    reconciliation_file: Optional[str]
    error_message: Optional[str]


class ReconciliationDetail(BaseModel):
    """Detailed reconciliation information."""

    id: int
    file_name: str
    file_received_at: str
    status: str
    total_records: int
    matched_records: int
    unmatched_records: int
    failed_records: int
    processed_at: Optional[str]
    error_details: Optional[str]
    unmatched_transactions: List[Dict[str, Any]]


class BankConnectionTest(BaseModel):
    """Bank SFTP connection test result."""

    task_id: str
    bank_code: str
    status: str
    message: str


class BankingDashboard(BaseModel):
    """Banking operations dashboard data."""

    period_days: int
    batch_trends: List[Dict[str, Any]]
    success_rates: Dict[str, Dict[str, float]]
    recent_failures: List[Dict[str, Any]]
    pending_reconciliations: int
    last_updated: str


class RetryQueueStatus(BaseModel):
    """Retry queue status information."""

    queue_size: int
    oldest_item_age: Optional[int]
    processing: bool
    last_processed: Optional[str]


class BankConfigurationUpdate(BaseModel):
    """Schema for updating bank configuration via API."""

    bank_name: Optional[str] = None
    sftp_host: Optional[str] = None
    sftp_port: Optional[int] = None
    sftp_username: Optional[str] = None
    upload_path: Optional[str] = None
    download_path: Optional[str] = None
    archive_path: Optional[str] = None
    file_format: Optional[str] = None
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    payment_file_pattern: Optional[str] = None
    reconciliation_file_pattern: Optional[str] = None
    is_active: Optional[bool] = None
    cutoff_time: Optional[str] = None
    retry_attempts: Optional[int] = None
    retry_delay_minutes: Optional[int] = None
