"""
Payment service for business logic
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Customer, Invoice, InvoicePaymentStatus, Payment, PaymentMethod
from app.schemas.payment import (
    CustomerBalance,
    DailyPaymentSummary,
    PaymentCreate,
    PaymentStats,
    PaymentUpdate,
)


class PaymentService:
    """Service for payment operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_payment_number(self) -> str:
        """Generate unique payment number"""
        # Format: PAY - YYYYMMDD - XXXX
        today = date.today()
        prefix = f"PAY-{today.strftime('%Y % m % d')}"

        # Find the last payment number for today
        query = (
            select(Payment)
            .where(Payment.payment_number.like(f"{prefix}%"))
            .order_by(desc(Payment.payment_number))
        )

        result = await self.db.execute(query)
        last_payment = result.scalar_one_or_none()

        if last_payment:
            # Extract the sequence number and increment
            last_seq = int(last_payment.payment_number.split("-")[-1])
            new_seq = str(last_seq + 1).zfill(4)
        else:
            new_seq = "0001"

        return f"{prefix}-{new_seq}"

    async def create_payment(
        self, payment_data: PaymentCreate, created_by: int
    ) -> Payment:
        """Create a new payment record"""
        # Generate payment number
        payment_number = await self.generate_payment_number()

        # Create payment
        payment = Payment(
            payment_number=payment_number,
            invoice_id=payment_data.invoice_id,
            payment_date=payment_data.payment_date,
            payment_method=payment_data.payment_method,
            amount=payment_data.amount,
            reference_number=payment_data.reference_number,
            bank_account=payment_data.bank_account,
            notes=payment_data.notes,
            is_verified=False,
            created_by=created_by,
        )

        self.db.add(payment)
        await self.db.flush()

        # Update invoice paid amount and payment status
        invoice = await self.db.get(Invoice, payment_data.invoice_id)
        invoice.paid_amount += payment_data.amount

        # Update payment status
        if invoice.paid_amount >= invoice.total_amount:
            invoice.payment_status = InvoicePaymentStatus.PAID
            invoice.paid_date = payment_data.payment_date
        elif invoice.paid_amount > 0:
            invoice.payment_status = InvoicePaymentStatus.PARTIAL

        await self.db.commit()
        await self.db.refresh(payment)

        # Load invoice relationship
        await self.db.execute(
            select(Payment)
            .where(Payment.id == payment.id)
            .options(selectinload(Payment.invoice))
        )

        return payment

    async def update_payment(
        self, payment_id: int, payment_update: PaymentUpdate
    ) -> Payment:
        """Update a payment record"""
        payment = await self.db.get(
            Payment, payment_id, options=[selectinload(Payment.invoice)]
        )

        # Store old amount for invoice update
        old_amount = payment.amount

        # Update fields
        update_data = payment_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(payment, field, value)

        # If amount changed, update invoice
        if "amount" in update_data and update_data["amount"] != old_amount:
            invoice = payment.invoice
            amount_diff = update_data["amount"] - old_amount
            invoice.paid_amount += amount_diff

            # Update payment status
            if invoice.paid_amount >= invoice.total_amount:
                invoice.payment_status = InvoicePaymentStatus.PAID
                invoice.paid_date = payment.payment_date
            elif invoice.paid_amount > 0:
                invoice.payment_status = InvoicePaymentStatus.PARTIAL
            else:
                invoice.payment_status = InvoicePaymentStatus.PENDING
                invoice.paid_date = None

        await self.db.commit()
        await self.db.refresh(payment)

        return payment

    async def verify_payment(
        self, payment_id: int, verified_by: int, notes: Optional[str] = None
    ) -> Payment:
        """Verify a payment for accounting"""
        payment = await self.db.get(Payment, payment_id)

        payment.is_verified = True
        payment.verified_by = verified_by
        payment.verified_at = datetime.now()

        if notes:
            payment.notes = (payment.notes or "") + f"\n核對備註: {notes}"

        await self.db.commit()
        await self.db.refresh(payment)

        return payment

    async def delete_payment(self, payment_id: int):
        """Delete a payment and update invoice"""
        payment = await self.db.get(
            Payment, payment_id, options=[selectinload(Payment.invoice)]
        )

        # Update invoice paid amount
        invoice = payment.invoice
        invoice.paid_amount -= payment.amount

        # Update payment status
        if invoice.paid_amount <= 0:
            invoice.payment_status = InvoicePaymentStatus.PENDING
            invoice.paid_date = None
        elif invoice.paid_amount < invoice.total_amount:
            invoice.payment_status = InvoicePaymentStatus.PARTIAL

        # Delete payment
        await self.db.delete(payment)
        await self.db.commit()

    async def get_period_stats(self, period: str) -> PaymentStats:
        """Get payment statistics for a period"""
        # Parse period (YYYYMM)
        year = int(period[:4])
        month = int(period[4:6])

        # Build date range
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Query payments for period
        query = select(Payment).where(
            and_(Payment.payment_date >= start_date, Payment.payment_date <= end_date)
        )

        result = await self.db.execute(query)
        payments = result.scalars().all()

        # Calculate statistics
        stats = {
            "period": period,
            "total_count": len(payments),
            "total_amount": sum(p.amount for p in payments),
            # By payment method
            "cash_count": sum(
                1 for p in payments if p.payment_method == PaymentMethod.CASH
            ),
            "cash_amount": sum(
                p.amount for p in payments if p.payment_method == PaymentMethod.CASH
            ),
            "transfer_count": sum(
                1 for p in payments if p.payment_method == PaymentMethod.TRANSFER
            ),
            "transfer_amount": sum(
                p.amount for p in payments if p.payment_method == PaymentMethod.TRANSFER
            ),
            "check_count": sum(
                1 for p in payments if p.payment_method == PaymentMethod.CHECK
            ),
            "check_amount": sum(
                p.amount for p in payments if p.payment_method == PaymentMethod.CHECK
            ),
            "credit_card_count": sum(
                1 for p in payments if p.payment_method == PaymentMethod.CREDIT_CARD
            ),
            "credit_card_amount": sum(
                p.amount
                for p in payments
                if p.payment_method == PaymentMethod.CREDIT_CARD
            ),
            "monthly_count": sum(
                1 for p in payments if p.payment_method == PaymentMethod.MONTHLY
            ),
            "monthly_amount": sum(
                p.amount for p in payments if p.payment_method == PaymentMethod.MONTHLY
            ),
            # Verification stats
            "verified_count": sum(1 for p in payments if p.is_verified),
            "verified_amount": sum(p.amount for p in payments if p.is_verified),
            "unverified_count": sum(1 for p in payments if not p.is_verified),
            "unverified_amount": sum(p.amount for p in payments if not p.is_verified),
            # Daily average
            "daily_average_count": len(payments) / ((end_date - start_date).days + 1),
            "daily_average_amount": sum(p.amount for p in payments)
            / ((end_date - start_date).days + 1),
        }

        return PaymentStats(**stats)

    async def get_daily_summary(self, date: date) -> DailyPaymentSummary:
        """Get daily payment summary"""
        # Query payments for the date
        query = select(Payment).where(Payment.payment_date == date)

        result = await self.db.execute(query)
        payments = result.scalars().all()

        # Calculate summary
        by_method = {}
        for method in PaymentMethod:
            method_payments = [p for p in payments if p.payment_method == method]
            if method_payments:
                by_method[method.value] = {
                    "count": len(method_payments),
                    "amount": sum(p.amount for p in method_payments),
                }

        summary = {
            "date": date,
            "total_count": len(payments),
            "total_amount": sum(p.amount for p in payments),
            "by_method": by_method,
            "verified_count": sum(1 for p in payments if p.is_verified),
            "verified_amount": sum(p.amount for p in payments if p.is_verified),
            "unverified_count": sum(1 for p in payments if not p.is_verified),
            "unverified_amount": sum(p.amount for p in payments if not p.is_verified),
        }

        return DailyPaymentSummary(**summary)

    async def get_customer_balance(
        self, customer_id: int, as_of_date: date
    ) -> CustomerBalance:
        """Get customer balance information"""
        # Get customer
        customer = await self.db.get(Customer, customer_id)
        if not customer:
            raise ValueError("Customer not found")

        # Query all invoices for customer up to as_of_date
        query = select(Invoice).where(
            and_(
                Invoice.customer_id == customer_id,
                Invoice.invoice_date <= as_of_date,
                Invoice.status == "issued",
            )
        )

        result = await self.db.execute(query)
        invoices = result.scalars().all()

        # Calculate totals
        total_invoiced = sum(inv.total_amount for inv in invoices)
        total_paid = sum(inv.paid_amount for inv in invoices)
        outstanding_balance = total_invoiced - total_paid

        # Calculate aging
        today = date.today()
        aging = {
            "current": 0,
            "overdue_30": 0,
            "overdue_60": 0,
            "overdue_90": 0,
            "overdue_over_90": 0,
        }

        outstanding_invoices = []
        oldest_unpaid_date = None

        for invoice in invoices:
            if invoice.paid_amount < invoice.total_amount:
                outstanding_amount = invoice.total_amount - invoice.paid_amount
                outstanding_invoices.append(invoice)

                if not oldest_unpaid_date or invoice.invoice_date < oldest_unpaid_date:
                    oldest_unpaid_date = invoice.invoice_date

                # Calculate days overdue
                if invoice.due_date:
                    days_overdue = (today - invoice.due_date).days

                    if days_overdue <= 0:
                        aging["current"] += outstanding_amount
                    elif days_overdue <= 30:
                        aging["overdue_30"] += outstanding_amount
                    elif days_overdue <= 60:
                        aging["overdue_60"] += outstanding_amount
                    elif days_overdue <= 90:
                        aging["overdue_90"] += outstanding_amount
                    else:
                        aging["overdue_over_90"] += outstanding_amount
                else:
                    aging["current"] += outstanding_amount

        # Calculate available credit
        available_credit = customer.credit_limit - outstanding_balance

        balance = {
            "customer_id": customer_id,
            "customer_code": customer.customer_code,
            "customer_name": customer.short_name,
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "outstanding_balance": outstanding_balance,
            **aging,
            "credit_limit": customer.credit_limit,
            "available_credit": available_credit,
            "is_credit_blocked": customer.is_credit_blocked,
            "outstanding_invoice_count": len(outstanding_invoices),
            "oldest_unpaid_date": oldest_unpaid_date,
        }

        return CustomerBalance(**balance)

    async def reconcile_payments(
        self, date_from: date, date_to: date
    ) -> Dict[str, Any]:
        """Reconcile payments for a date range"""
        # Query payments in date range
        query = (
            select(Payment)
            .where(
                and_(Payment.payment_date >= date_from, Payment.payment_date <= date_to)
            )
            .options(selectinload(Payment.invoice))
        )

        result = await self.db.execute(query)
        payments = result.scalars().all()

        # Perform reconciliation checks
        issues = []
        matched_count = 0
        matched_amount = 0
        unmatched_count = 0
        unmatched_amount = 0

        for payment in payments:
            # Check if payment matches invoice
            if payment.invoice:
                # Various validation checks
                if payment.amount > payment.invoice.total_amount:
                    issues.append(
                        {
                            "payment_id": payment.id,
                            "issue": "付款金額超過發票總額",
                            "payment_amount": payment.amount,
                            "invoice_amount": payment.invoice.total_amount,
                        }
                    )
                    unmatched_count += 1
                    unmatched_amount += payment.amount
                else:
                    matched_count += 1
                    matched_amount += payment.amount
            else:
                issues.append({"payment_id": payment.id, "issue": "找不到對應發票"})
                unmatched_count += 1
                unmatched_amount += payment.amount

        return {
            "date_from": date_from,
            "date_to": date_to,
            "total_payments": len(payments),
            "total_amount": sum(p.amount for p in payments),
            "matched_count": matched_count,
            "matched_amount": matched_amount,
            "unmatched_count": unmatched_count,
            "unmatched_amount": unmatched_amount,
            "issues": issues,
        }
