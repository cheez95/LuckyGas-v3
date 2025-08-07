"""
Invoice management API endpoints
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.customer import Customer
from app.models.order import Order
from app.models.user import User
from app.schemas.invoice import (
    InvoiceBulkAction,
    InvoiceCreate,
    InvoiceResponse,
    InvoiceStats,
    InvoiceUpdate,
)
from app.services.einvoice_service import EInvoiceService
from app.services.invoice_service import InvoiceService
from app.models.invoice import Invoice
from app.models.invoice import InvoicePaymentStatus
from app.models.invoice import InvoiceStatus
from sqlalchemy import desc

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/", response_model=InvoiceResponse)
async def create_invoice(
    invoice_data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new invoice"""
    # Check if user has permission
    if current_user.role not in ["super_admin", "manager", "office_staf"]:
        raise HTTPException(status_code=403, detail="沒有權限建立發票")

    # Verify customer exists
    customer = await db.get(Customer, invoice_data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")

    # If order_id provided, verify it exists and belongs to customer
    if invoice_data.order_id:
        order = await db.get(Order, invoice_data.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="訂單不存在")
        if order.customer_id != invoice_data.customer_id:
            raise HTTPException(status_code=400, detail="訂單不屬於此客戶")

    # Create invoice using service
    service = InvoiceService(db)
    invoice = await service.create_invoice(
        invoice_data=invoice_data, created_by=current_user.id
    )

    return invoice


@router.get("/", response_model=List[InvoiceResponse])
async def get_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_id: Optional[int] = None,
    status: Optional[InvoiceStatus] = None,
    payment_status: Optional[InvoicePaymentStatus] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of invoices with filtering"""
    query = select(Invoice).options(
        selectinload(Invoice.customer),
        selectinload(Invoice.items),
        selectinload(Invoice.order),
    )

    # Apply filters
    filters = []

    if customer_id:
        filters.append(Invoice.customer_id == customer_id)

    if status:
        filters.append(Invoice.status == status)

    if payment_status:
        filters.append(Invoice.payment_status == payment_status)

    if date_from:
        filters.append(Invoice.invoice_date >= date_from)

    if date_to:
        filters.append(Invoice.invoice_date <= date_to)

    if search:
        # Search in invoice number, customer name, or buyer name
        filters.append(
            or_(
                Invoice.invoice_number.ilike(f"%{search}%"),
                Invoice.buyer_name.ilike(f"%{search}%"),
                Invoice.buyer_tax_id.ilike(f"%{search}%"),
            )
        )

    if filters:
        query = query.where(and_(*filters))

    # Order by date descending
    query = query.order_by(desc(Invoice.invoice_date), desc(Invoice.id))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    invoices = result.scalars().all()

    return invoices


@router.get("/stats", response_model=InvoiceStats)
async def get_invoice_stats(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get invoice statistics for a period"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看統計資料")

    service = InvoiceService(db)
    stats = await service.get_period_stats(period)

    return stats


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single invoice details"""
    invoice = await db.get(
        Invoice,
        invoice_id,
        options=[
            selectinload(Invoice.customer),
            selectinload(Invoice.items),
            selectinload(Invoice.order),
            selectinload(Invoice.payments),
            selectinload(Invoice.credit_notes),
        ],
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")

    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update invoice (only draft invoices can be fully edited)"""
    if current_user.role not in ["super_admin", "manager", "office_staf"]:
        raise HTTPException(status_code=403, detail="沒有權限更新發票")

    invoice = await db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")

    # Only draft invoices can be fully edited
    if invoice.status != InvoiceStatus.DRAFT and not current_user.role == "super_admin":
        raise HTTPException(
            status_code=400, detail="只有草稿發票可以修改，已開立發票請使用作廢或折讓"
        )

    service = InvoiceService(db)
    updated_invoice = await service.update_invoice(
        invoice_id=invoice_id, invoice_update=invoice_update
    )

    return updated_invoice


@router.post("/{invoice_id}/issue", response_model=InvoiceResponse)
async def issue_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue a draft invoice (submit to government)"""
    if current_user.role not in ["super_admin", "manager", "office_staf"]:
        raise HTTPException(status_code=403, detail="沒有權限開立發票")

    invoice = await db.get(
        Invoice,
        invoice_id,
        options=[selectinload(Invoice.items), selectinload(Invoice.customer)],
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")

    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只有草稿發票可以開立")

    # Submit to e - invoice service
    einvoice_service = EInvoiceService()
    service = InvoiceService(db)

    try:
        issued_invoice = await service.issue_invoice(
            invoice_id=invoice_id, einvoice_service=einvoice_service
        )
        return issued_invoice
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"開立發票失敗: {str(e)}")


@router.post("/{invoice_id}/void", response_model=InvoiceResponse)
async def void_invoice(
    invoice_id: int,
    reason: str = Query(..., min_length=1, max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Void an issued invoice"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限作廢發票")

    invoice = await db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")

    if invoice.status != InvoiceStatus.ISSUED:
        raise HTTPException(status_code=400, detail="只有已開立發票可以作廢")

    service = InvoiceService(db)
    einvoice_service = EInvoiceService()

    try:
        voided_invoice = await service.void_invoice(
            invoice_id=invoice_id, reason=reason, einvoice_service=einvoice_service
        )
        return voided_invoice
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"作廢發票失敗: {str(e)}")


@router.post("/{invoice_id}/print")
async def print_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate printable invoice PDF"""
    invoice = await db.get(
        Invoice,
        invoice_id,
        options=[selectinload(Invoice.items), selectinload(Invoice.customer)],
    )

    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")

    if invoice.status != InvoiceStatus.ISSUED:
        raise HTTPException(status_code=400, detail="只有已開立發票可以列印")

    service = InvoiceService(db)
    pdf_bytes = await service.generate_invoice_pdf(invoice)

    # Mark as printed
    invoice.is_printed = True
    await db.commit()

    return {
        "filename": f"invoice_{invoice.invoice_number}.pd",
        "content": pdf_bytes.hex(),  # Return as hex string
    }


@router.post("/bulk - action", response_model=dict)
async def bulk_invoice_action(
    action: InvoiceBulkAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Perform bulk actions on invoices"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限執行批次操作")

    service = InvoiceService(db)

    if action.action == "issue":
        einvoice_service = EInvoiceService()
        results = await service.bulk_issue_invoices(
            invoice_ids=action.invoice_ids, einvoice_service=einvoice_service
        )
    elif action.action == "print":
        results = await service.bulk_print_invoices(action.invoice_ids)
    elif action.action == "export":
        results = await service.export_invoices(
            invoice_ids=action.invoice_ids, format=action.export_format
        )
    else:
        raise HTTPException(status_code=400, detail="不支援的批次操作")

    return results


@router.get("/download/{period}")
async def download_period_invoices(
    period: str = Path(..., pattern="^\\d{6}$"),
    format: str = Query("excel", pattern="^(excel|csv|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download all invoices for a period"""
    if current_user.role not in ["super_admin", "manager", "office_staf"]:
        raise HTTPException(status_code=403, detail="沒有權限下載發票")

    service = InvoiceService(db)

    if format == "excel":
        file_data = await service.export_period_excel(period)
        filename = f"invoices_{period}.xlsx"
    elif format == "csv":
        file_data = await service.export_period_csv(period)
        filename = f"invoices_{period}.csv"
    else:  # pdf
        file_data = await service.export_period_pdf(period)
        filename = f"invoices_{period}.pdf"

    return {"filename": filename, "content": file_data.hex()}
