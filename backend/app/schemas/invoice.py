"""
Invoice schemas for API requests and responses
"""

import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.invoice import (
    InvoicePaymentStatus,
    InvoiceStatus,
    InvoiceType,
    PaymentMethod,
)


class InvoiceItemBase(BaseModel):
    """Base schema for invoice items"""

    sequence: int = Field(..., ge=1, description="項次")
    product_code: Optional[str] = Field(None, max_length=50)
    product_name: str = Field(..., min_length=1, max_length=200, description="品名")
    quantity: float = Field(..., gt=0, description="數量")
    unit: str = Field("個", max_length=20, description="單位")
    unit_price: float = Field(..., ge=0, description="單價")
    amount: float = Field(..., ge=0, description="小計")
    tax_type: str = Field("1", pattern="^[1 - 3]$", description="課稅別")
    tax_amount: float = Field(0, ge=0, description="稅額")
    remark: Optional[str] = Field(None, max_length=200)


class InvoiceItemCreate(InvoiceItemBase):
    """Schema for creating invoice items"""


class InvoiceItemResponse(InvoiceItemBase):
    """Schema for invoice item responses"""

    id: int
    invoice_id: int

    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    """Base schema for invoices"""

    customer_id: int
    order_id: Optional[int] = None
    invoice_type: InvoiceType = InvoiceType.B2B
    invoice_date: date

    # Buyer information
    buyer_tax_id: Optional[str] = Field(None, max_length=8, pattern="^[0 - 9]{8}$")
    buyer_name: str = Field(..., min_length=1, max_length=200)
    buyer_address: Optional[str] = Field(None, max_length=500)

    # Amounts
    sales_amount: float = Field(..., ge=0, description="銷售額")
    tax_type: str = Field("1", pattern="^[1 - 3]$")
    tax_rate: float = Field(0.05, ge=0, le=1)
    tax_amount: float = Field(..., ge=0)
    total_amount: float = Field(..., ge=0)

    # Payment
    payment_method: Optional[PaymentMethod] = None
    due_date: Optional[date] = None

    # Notes
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("buyer_tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^\d{8}$", v):
            raise ValueError("統一編號必須是8位數字")
        return v


class InvoiceCreate(InvoiceBase):
    """Schema for creating invoices"""

    items: List[InvoiceItemCreate] = Field(..., min_items=1)

    @field_validator("total_amount")
    @classmethod
    def validate_total(cls, v: float, values: Dict[str, Any]) -> float:
        expected_total = values.data.get("sales_amount", 0) + values.data.get(
            "tax_amount", 0
        )
        if abs(v - expected_total) > 0.01:  # Allow small rounding differences
            raise ValueError("總額必須等於銷售額加稅額")
        return v


class InvoiceUpdate(BaseModel):
    """Schema for updating invoices"""

    buyer_tax_id: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_address: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = None


class PaymentResponse(BaseModel):
    """Schema for payment responses"""

    id: int
    payment_number: str
    payment_date: date
    payment_method: PaymentMethod
    amount: float
    reference_number: Optional[str]
    is_verified: bool
    verified_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreditNoteResponse(BaseModel):
    """Schema for credit note responses"""

    id: int
    credit_note_number: str
    credit_date: date
    reason: str
    credit_amount: float
    tax_amount: float
    total_amount: float
    status: InvoiceStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(InvoiceBase):
    """Schema for invoice responses"""

    id: int
    invoice_number: str
    invoice_track: str
    invoice_no: str
    random_code: Optional[str]
    period: str
    status: InvoiceStatus
    payment_status: InvoicePaymentStatus

    # E - invoice fields
    einvoice_id: Optional[str]
    qr_code_left: Optional[str]
    qr_code_right: Optional[str]
    bar_code: Optional[str]
    submitted_at: Optional[datetime]
    is_printed: bool

    # Payment tracking
    paid_amount: float
    paid_date: Optional[date]

    # Void / Allowance
    void_reason: Optional[str]
    void_date: Optional[date]
    allowance_number: Optional[str]

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Related data
    items: List[InvoiceItemResponse] = []
    payments: List[PaymentResponse] = []
    credit_notes: List[CreditNoteResponse] = []

    # Customer info (optional)
    customer_name: Optional[str] = None
    customer_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, obj):
        # Add customer info if available
        data = {}
        if hasattr(obj, "customer") and obj.customer:
            data["customer_name"] = obj.customer.short_name
            data["customer_code"] = obj.customer.customer_code

        return cls.model_validate(obj, update=data)


class InvoiceSearchParams(BaseModel):
    """Parameters for searching invoices"""

    customer_id: Optional[int] = None
    status: Optional[InvoiceStatus] = None
    payment_status: Optional[InvoicePaymentStatus] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    invoice_number: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None


class InvoiceStats(BaseModel):
    """Invoice statistics for a period"""

    period: str
    total_count: int
    issued_count: int
    void_count: int

    # Amounts
    total_sales_amount: float
    total_tax_amount: float
    total_amount: float

    # Payment stats
    paid_count: int
    paid_amount: float
    unpaid_count: int
    unpaid_amount: float
    overdue_count: int
    overdue_amount: float

    # By type
    b2b_count: int
    b2b_amount: float
    b2c_count: int
    b2c_amount: float


class InvoiceBulkAction(BaseModel):
    """Schema for bulk invoice actions"""

    action: str = Field(..., pattern="^(issue|void|print|export)$")
    invoice_ids: List[int] = Field(..., min_items=1)
    export_format: Optional[str] = Field("excel", pattern="^(excel|csv|pdf)$")
    void_reason: Optional[str] = Field(None, max_length=200)
