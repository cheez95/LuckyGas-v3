"""
Payment schemas for API requests and responses
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.invoice import PaymentMethod


class PaymentBase(BaseModel):
    """Base schema for payments"""

    invoice_id: int
    payment_date: date
    payment_method: PaymentMethod
    amount: float = Field(..., gt=0, description="付款金額")
    reference_number: Optional[str] = Field(
        None, max_length=100, description="轉帳編號 / 支票號碼"
    )
    bank_account: Optional[str] = Field(None, max_length=50, description="銀行帳號")
    notes: Optional[str] = Field(None, max_length=500)


class PaymentCreate(PaymentBase):
    """Schema for creating payments"""


class PaymentUpdate(BaseModel):
    """Schema for updating payments"""

    payment_date: Optional[date] = None
    payment_method: Optional[PaymentMethod] = None
    amount: Optional[float] = Field(None, gt=0)
    reference_number: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


class PaymentVerification(BaseModel):
    """Schema for payment verification"""

    notes: Optional[str] = Field(None, max_length=500, description="核對備註")


class InvoiceInfo(BaseModel):
    """Invoice information for payment response"""

    id: int
    invoice_number: str
    buyer_name: str
    total_amount: float
    paid_amount: float

    model_config = ConfigDict(from_attributes=True)


class PaymentResponse(PaymentBase):
    """Schema for payment responses"""

    id: int
    payment_number: str
    is_verified: bool
    verified_by: Optional[int]
    verified_at: Optional[datetime]
    created_at: datetime
    created_by: int

    # Related invoice info
    invoice: Optional[InvoiceInfo] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentSearchParams(BaseModel):
    """Parameters for searching payments"""

    invoice_id: Optional[int] = None
    payment_method: Optional[PaymentMethod] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    is_verified: Optional[bool] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None


class PaymentStats(BaseModel):
    """Payment statistics for a period"""

    period: str
    total_count: int
    total_amount: float

    # By payment method
    cash_count: int
    cash_amount: float
    transfer_count: int
    transfer_amount: float
    check_count: int
    check_amount: float
    credit_card_count: int
    credit_card_amount: float
    monthly_count: int
    monthly_amount: float

    # Verification stats
    verified_count: int
    verified_amount: float
    unverified_count: int
    unverified_amount: float

    # Daily average
    daily_average_count: float
    daily_average_amount: float


class DailyPaymentSummary(BaseModel):
    """Daily payment summary"""

    date: date
    total_count: int
    total_amount: float

    # By payment method breakdown
    by_method: Dict[str, Dict[str, float]]  # method -> {count, amount}

    # Verification status
    verified_count: int
    verified_amount: float
    unverified_count: int
    unverified_amount: float


class CustomerBalance(BaseModel):
    """Customer balance information"""

    customer_id: int
    customer_code: str
    customer_name: str

    # Invoice totals
    total_invoiced: float
    total_paid: float
    outstanding_balance: float

    # Aging
    current: float  # Not due yet
    overdue_30: float  # 1 - 30 days overdue
    overdue_60: float  # 31 - 60 days overdue
    overdue_90: float  # 61 - 90 days overdue
    overdue_over_90: float  # >90 days overdue

    # Credit info
    credit_limit: float
    available_credit: float
    is_credit_blocked: bool

    # Outstanding invoices
    outstanding_invoice_count: int
    oldest_unpaid_date: Optional[date]


class ReconciliationResult(BaseModel):
    """Result of payment reconciliation"""

    date_from: date
    date_to: date

    # Totals
    total_payments: int
    total_amount: float

    # Matched / Unmatched
    matched_count: int
    matched_amount: float
    unmatched_count: int
    unmatched_amount: float

    # Issues found
    issues: List[Dict[str, Any]]
