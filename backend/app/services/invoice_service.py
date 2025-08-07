"""
Invoice service for business logic
"""

import random
import string
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Invoice,
    InvoiceItem,
    InvoicePaymentStatus,
    InvoiceStatus,
)
from app.schemas.invoice import InvoiceCreate, InvoiceStats, InvoiceUpdate


class InvoiceService:
    """Service for invoice operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_invoice_number(self, invoice_date: date) -> Dict[str, str]:
        """Generate unique invoice number for Taiwan e - invoice format"""
        # Get current period
        period = invoice_date.strftime("%Y % m")

        # For production, these would come from government allocation
        # For now, use test prefixes
        tracks = ["AB", "CD", "EF", "GH"]
        track = random.choice(tracks)

        # Find the last invoice number for this track and period
        query = (
            select(Invoice)
            .where(and_(Invoice.invoice_track == track, Invoice.period == period))
            .order_by(desc(Invoice.invoice_no))
        )

        result = await self.db.execute(query)
        last_invoice = result.scalar_one_or_none()

        if last_invoice:
            # Increment the number
            last_no = int(last_invoice.invoice_no)
            new_no = str(last_no + 1).zfill(8)
        else:
            # Start from 00000001
            new_no = "00000001"

        # Generate random code (4 digits)
        random_code = "".join(random.choices(string.digits, k=4))

        return {
            "invoice_number": f"{track}{new_no}",
            "invoice_track": track,
            "invoice_no": new_no,
            "random_code": random_code,
            "period": period,
        }

    async def create_invoice(
        self, invoice_data: InvoiceCreate, created_by: int
    ) -> Invoice:
        """Create a new invoice"""
        # Generate invoice number
        invoice_numbers = await self.generate_invoice_number(invoice_data.invoice_date)

        # Create invoice
        invoice = Invoice(
            **invoice_numbers,
            customer_id=invoice_data.customer_id,
            order_id=invoice_data.order_id,
            invoice_type=invoice_data.invoice_type,
            invoice_date=invoice_data.invoice_date,
            buyer_tax_id=invoice_data.buyer_tax_id,
            buyer_name=invoice_data.buyer_name,
            buyer_address=invoice_data.buyer_address,
            sales_amount=invoice_data.sales_amount,
            tax_type=invoice_data.tax_type,
            tax_rate=invoice_data.tax_rate,
            tax_amount=invoice_data.tax_amount,
            total_amount=invoice_data.total_amount,
            payment_method=invoice_data.payment_method,
            due_date=invoice_data.due_date
            or invoice_data.invoice_date + timedelta(days=30),
            notes=invoice_data.notes,
            status=InvoiceStatus.DRAFT,
            payment_status=InvoicePaymentStatus.PENDING,
            created_by=created_by,
        )

        self.db.add(invoice)
        await self.db.flush()

        # Add invoice items
        for item_data in invoice_data.items:
            item = InvoiceItem(invoice_id=invoice.id, **item_data.model_dump())
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(invoice)

        # Load relationships
        await self.db.execute(
            select(Invoice)
            .where(Invoice.id == invoice.id)
            .options(selectinload(Invoice.items), selectinload(Invoice.customer))
        )

        return invoice

    async def update_invoice(
        self, invoice_id: int, invoice_update: InvoiceUpdate
    ) -> Invoice:
        """Update an invoice"""
        invoice = await self.db.get(Invoice, invoice_id)

        # Update fields
        update_data = invoice_update.model_dump(exclude_unset=True, exclude={"items"})
        for field, value in update_data.items():
            setattr(invoice, field, value)

        # Update items if provided
        if invoice_update.items is not None:
            # Delete existing items
            await self.db.execute(
                select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
            )

            # Add new items
            for item_data in invoice_update.items:
                item = InvoiceItem(invoice_id=invoice_id, **item_data.model_dump())
                self.db.add(item)

        invoice.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def issue_invoice(self, invoice_id: int, einvoice_service: Any) -> Invoice:
        """Issue an invoice to government e - invoice platform"""
        invoice = await self.db.get(
            Invoice,
            invoice_id,
            options=[selectinload(Invoice.items), selectinload(Invoice.customer)],
        )

        # Generate QR codes and barcode
        qr_left, qr_right = self._generate_qr_codes(invoice)
        barcode = self._generate_barcode(invoice)

        # Submit to e - invoice platform
        result = await einvoice_service.submit_invoice(invoice)

        # Update invoice
        invoice.status = InvoiceStatus.ISSUED
        invoice.einvoice_id = result.get("einvoice_id")
        invoice.qr_code_left = qr_left
        invoice.qr_code_right = qr_right
        invoice.bar_code = barcode
        invoice.submitted_at = datetime.now()
        invoice.submission_response = result

        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def void_invoice(
        self, invoice_id: int, reason: str, einvoice_service: Any
    ) -> Invoice:
        """Void an issued invoice"""
        invoice = await self.db.get(Invoice, invoice_id)

        # Submit void request to e - invoice platform
        result = await einvoice_service.void_invoice(
            einvoice_id=invoice.einvoice_id, reason=reason
        )

        # Update invoice
        invoice.status = InvoiceStatus.VOID
        invoice.void_reason = reason
        invoice.void_date = date.today()
        invoice.payment_status = InvoicePaymentStatus.CANCELLED

        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def get_period_stats(self, period: str) -> InvoiceStats:
        """Get invoice statistics for a period"""
        # Parse period (YYYYMM)
        year = int(period[:4])
        month = int(period[4:6])

        # Build date range
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Query invoices for period
        query = select(Invoice).where(
            and_(Invoice.invoice_date >= start_date, Invoice.invoice_date <= end_date)
        )

        result = await self.db.execute(query)
        invoices = result.scalars().all()

        # Calculate statistics
        stats = {
            "period": period,
            "total_count": len(invoices),
            "issued_count": sum(
                1 for inv in invoices if inv.status == InvoiceStatus.ISSUED
            ),
            "void_count": sum(
                1 for inv in invoices if inv.status == InvoiceStatus.VOID
            ),
            "total_sales_amount": sum(inv.sales_amount for inv in invoices),
            "total_tax_amount": sum(inv.tax_amount for inv in invoices),
            "total_amount": sum(inv.total_amount for inv in invoices),
            "paid_count": sum(
                1 for inv in invoices if inv.payment_status == InvoicePaymentStatus.PAID
            ),
            "paid_amount": sum(inv.paid_amount for inv in invoices),
            "unpaid_count": sum(
                1
                for inv in invoices
                if inv.payment_status
                in [InvoicePaymentStatus.PENDING, InvoicePaymentStatus.PARTIAL]
            ),
            "unpaid_amount": sum(
                inv.total_amount - inv.paid_amount for inv in invoices
            ),
            "overdue_count": sum(
                1
                for inv in invoices
                if inv.payment_status == InvoicePaymentStatus.OVERDUE
            ),
            "overdue_amount": sum(
                inv.total_amount - inv.paid_amount
                for inv in invoices
                if inv.payment_status == InvoicePaymentStatus.OVERDUE
            ),
            "b2b_count": sum(1 for inv in invoices if inv.invoice_type == "B2B"),
            "b2b_amount": sum(
                inv.total_amount for inv in invoices if inv.invoice_type == "B2B"
            ),
            "b2c_count": sum(1 for inv in invoices if inv.invoice_type == "B2C"),
            "b2c_amount": sum(
                inv.total_amount for inv in invoices if inv.invoice_type == "B2C"
            ),
        }

        return InvoiceStats(**stats)

    async def bulk_issue_invoices(
        self, invoice_ids: List[int], einvoice_service: Any
    ) -> Dict[str, Any]:
        """Bulk issue invoices"""
        success_count = 0
        failed_count = 0
        errors = []

        for invoice_id in invoice_ids:
            try:
                await self.issue_invoice(invoice_id, einvoice_service)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({"invoice_id": invoice_id, "error": str(e)})

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors,
        }

    async def generate_invoice_pdf(self, invoice: Invoice) -> bytes:
        """Generate PDF for invoice printing"""
        # This would use a PDF generation library
        # For now, return placeholder
        return b"PDF content would be here"

    async def export_period_excel(self, period: str) -> bytes:
        """Export invoices for a period to Excel"""
        # This would use openpyxl or similar
        # For now, return placeholder
        return b"Excel content would be here"

    def _generate_qr_codes(self, invoice: Invoice) -> tuple[str, str]:
        """Generate QR code content for Taiwan e - invoice"""
        # Left QR code contains basic info
        qr_left = f"{invoice.invoice_number}{invoice.random_code}{invoice.invoice_date.strftime('%Y % m % d')}"

        # Right QR code contains detailed info
        qr_right = f"{invoice.total_amount}:{invoice.sales_amount}:{invoice.buyer_tax_id or '00000000'}"

        return qr_left, qr_right

    def _generate_barcode(self, invoice: Invoice) -> str:
        """Generate barcode for Taiwan e - invoice"""
        # Barcode format: Period(6) + Invoice Number(10) + Random Code(4)
        period_yymm = invoice.invoice_date.strftime("%y % m")  # YY format for barcode
        return f"{period_yymm}{invoice.invoice_number}{invoice.random_code}"
