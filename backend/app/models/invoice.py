"""
Invoice models for financial management
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    """Invoice status enumeration"""

    DRAFT = "draft"  # 草稿
    ISSUED = "issued"  # 已開立
    VOID = "void"  # 作廢
    ALLOWANCE = "allowance"  # 折讓
    CANCELLED = "cancelled"  # 取消


class InvoiceType(str, enum.Enum):
    """Invoice type enumeration"""

    B2B = "B2B"  # 電子發票 (B2B)
    B2C = "B2C"  # 電子發票 (B2C)
    DONATION = "donation"  # 捐贈
    PAPER = "paper"  # 紙本發票


class InvoicePaymentStatus(str, enum.Enum):
    """Invoice payment status enumeration"""

    PENDING = "pending"  # 待付款
    PARTIAL = "partial"  # 部分付款
    PAID = "paid"  # 已付款
    OVERDUE = "overdue"  # 逾期
    CANCELLED = "cancelled"  # 取消


class PaymentMethod(str, enum.Enum):
    """Payment method enumeration"""

    CASH = "cash"  # 現金
    TRANSFER = "transfer"  # 轉帳
    CHECK = "check"  # 支票
    CREDIT_CARD = "credit_card"  # 信用卡
    MONTHLY = "monthly"  # 月結


class Invoice(Base):
    """Invoice records for gas deliveries"""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    # Invoice identification
    invoice_number = Column(
        String(20), unique=True, nullable=False, index=True
    )  # 發票號碼 (e.g., AB12345678)
    invoice_track = Column(String(2), nullable=False)  # 發票字軌 (e.g., AB)
    invoice_no = Column(String(8), nullable=False)  # 發票號碼 (e.g., 12345678)
    random_code = Column(String(4))  # 隨機碼 (4 digits)

    # Related entities
    customer_id = Column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)

    # Invoice details
    invoice_type = Column(SQLEnum(InvoiceType), default=InvoiceType.B2B, nullable=False)
    invoice_date = Column(Date, nullable=False, index=True)
    period = Column(String(6), nullable=False)  # YYYYMM format (e.g., 202501)

    # Buyer information
    buyer_tax_id = Column(String(8))  # 買方統編
    buyer_name = Column(String(200))  # 買方名稱
    buyer_address = Column(String(500))  # 買方地址

    # Amounts (all amounts are in TWD)
    sales_amount = Column(Float, nullable=False, default=0)  # 銷售額 (未稅)
    tax_type = Column(String(1), default="1")  # 課稅別 (1:應稅, 2:零稅率, 3:免稅)
    tax_rate = Column(Float, default=0.05)  # 稅率 (5%)
    tax_amount = Column(Float, nullable=False, default=0)  # 稅額
    total_amount = Column(Float, nullable=False, default=0)  # 總計 (含稅)

    # Status
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    payment_status = Column(
        SQLEnum(InvoicePaymentStatus),
        default=InvoicePaymentStatus.PENDING,
        nullable=False,
    )
    payment_method = Column(SQLEnum(PaymentMethod), nullable=True)

    # Government e-invoice fields
    einvoice_id = Column(String(50), unique=True, index=True)  # 電子發票ID
    qr_code_left = Column(String(200))  # QR Code 左邊內容
    qr_code_right = Column(String(200))  # QR Code 右邊內容
    bar_code = Column(String(100))  # 一維條碼

    # Submission tracking
    submitted_at = Column(DateTime, nullable=True)  # 上傳時間
    submission_response = Column(JSON, nullable=True)  # 上傳回應
    is_printed = Column(Boolean, default=False)  # 是否已列印

    # Void/Allowance tracking
    void_reason = Column(String(200))  # 作廢原因
    void_date = Column(Date)  # 作廢日期
    allowance_number = Column(String(20))  # 折讓單號

    # Payment tracking
    due_date = Column(Date)  # 付款期限
    paid_amount = Column(Float, default=0)  # 已付金額
    paid_date = Column(Date)  # 付款日期

    # Notes and metadata
    notes = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    order = relationship("Order", back_populates="invoice")
    items = relationship(
        "InvoiceItem", back_populates="invoice", cascade="all, delete-orphan"
    )
    payments = relationship(
        "Payment", back_populates="invoice", cascade="all, delete-orphan"
    )
    credit_notes = relationship("CreditNote", back_populates="original_invoice")

    # Indexes
    __table_args__ = (
        Index("idx_invoice_date_status", "invoice_date", "status"),
        Index("idx_invoice_customer", "customer_id", "invoice_date"),
        Index("idx_invoice_payment", "payment_status", "due_date"),
    )

    def __repr__(self):
        return f"<Invoice {self.invoice_number} - {self.buyer_name}>"


class InvoiceItem(Base):
    """Individual items on an invoice"""

    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)

    # Item details
    sequence = Column(Integer, nullable=False)  # 項次
    product_code = Column(String(50))  # 產品代碼
    product_name = Column(String(200), nullable=False)  # 品名

    # Quantities and amounts
    quantity = Column(Float, nullable=False)  # 數量
    unit = Column(String(20), default="個")  # 單位
    unit_price = Column(Float, nullable=False)  # 單價
    amount = Column(Float, nullable=False)  # 小計 (未稅)

    # Tax
    tax_type = Column(String(1), default="1")  # 課稅別
    tax_amount = Column(Float, default=0)  # 稅額

    # Notes
    remark = Column(String(200))  # 備註

    # Relationships
    invoice = relationship("Invoice", back_populates="items")

    def __repr__(self):
        return f"<InvoiceItem {self.product_name} x {self.quantity}>"


class Payment(Base):
    """Payment records for invoices"""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # Payment identification
    payment_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)

    # Payment details
    payment_date = Column(Date, nullable=False, index=True)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    amount = Column(Float, nullable=False)

    # Payment reference
    reference_number = Column(String(100))  # 轉帳編號/支票號碼
    bank_account = Column(String(50))  # 銀行帳號

    # Status
    is_verified = Column(Boolean, default=False)  # 是否已核對
    verified_by = Column(Integer, ForeignKey("users.id"))
    verified_at = Column(DateTime)

    # Notes
    notes = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.payment_number} - {self.amount}>"


class CreditNote(Base):
    """Credit notes for invoice corrections"""

    __tablename__ = "credit_notes"

    id = Column(Integer, primary_key=True, index=True)

    # Credit note identification
    credit_note_number = Column(String(20), unique=True, nullable=False, index=True)
    original_invoice_id = Column(
        Integer, ForeignKey("invoices.id"), nullable=False, index=True
    )

    # Credit note details
    credit_date = Column(Date, nullable=False, index=True)
    reason = Column(String(200), nullable=False)  # 折讓原因

    # Amounts
    credit_amount = Column(Float, nullable=False)  # 折讓金額 (未稅)
    tax_amount = Column(Float, default=0)  # 折讓稅額
    total_amount = Column(Float, nullable=False)  # 折讓總額 (含稅)

    # Government submission
    einvoice_id = Column(String(50), unique=True, index=True)
    submitted_at = Column(DateTime)
    submission_response = Column(JSON)

    # Status
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    original_invoice = relationship("Invoice", back_populates="credit_notes")

    def __repr__(self):
        return f"<CreditNote {self.credit_note_number}>"
