"""
Financial reporting service
"""

import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (Customer, Invoice, InvoiceItem, InvoicePaymentStatus,
                        InvoiceStatus, Order, Payment)


class FinancialReportService:
    """Service for generating financial reports"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_revenue_summary(self, period: str) -> Dict[str, Any]:
        """Get revenue summary for a period"""
        year = int(period[:4])
        month = int(period[4:6])

        # Date range
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Query invoices
        query = select(Invoice).where(
            and_(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date,
                Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.VOID]),
            )
        )

        result = await self.db.execute(query)
        invoices = result.scalars().all()

        # Calculate summary
        gross_revenue = sum(
            inv.sales_amount for inv in invoices if inv.status == InvoiceStatus.ISSUED
        )
        tax_collected = sum(
            inv.tax_amount for inv in invoices if inv.status == InvoiceStatus.ISSUED
        )
        total_revenue = gross_revenue + tax_collected

        void_amount = sum(
            inv.total_amount for inv in invoices if inv.status == InvoiceStatus.VOID
        )

        # Payment collection
        collected = sum(
            inv.paid_amount for inv in invoices if inv.status == InvoiceStatus.ISSUED
        )
        outstanding = total_revenue - collected

        # By customer type
        b2b_revenue = sum(
            inv.total_amount
            for inv in invoices
            if inv.status == InvoiceStatus.ISSUED and inv.invoice_type == "B2B"
        )
        b2c_revenue = sum(
            inv.total_amount
            for inv in invoices
            if inv.status == InvoiceStatus.ISSUED and inv.invoice_type == "B2C"
        )

        return {
            "period": period,
            "gross_revenue": gross_revenue,
            "tax_collected": tax_collected,
            "total_revenue": total_revenue,
            "void_amount": void_amount,
            "net_revenue": total_revenue - void_amount,
            "collected_amount": collected,
            "outstanding_amount": outstanding,
            "collection_rate": (
                (collected / total_revenue * 100) if total_revenue > 0 else 0
            ),
            "b2b_revenue": b2b_revenue,
            "b2c_revenue": b2c_revenue,
            "invoice_count": sum(
                1 for inv in invoices if inv.status == InvoiceStatus.ISSUED
            ),
            "void_count": sum(
                1 for inv in invoices if inv.status == InvoiceStatus.VOID
            ),
        }

    async def get_accounts_receivable_report(
        self, as_of_date: date, customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get accounts receivable aging report"""
        # Base query
        query = (
            select(Invoice)
            .where(
                and_(
                    Invoice.invoice_date <= as_of_date,
                    Invoice.status == InvoiceStatus.ISSUED,
                    Invoice.payment_status != InvoicePaymentStatus.PAID,
                )
            )
            .options(selectinload(Invoice.customer))
        )

        if customer_id:
            query = query.where(Invoice.customer_id == customer_id)

        result = await self.db.execute(query)
        invoices = result.scalars().all()

        # Calculate aging buckets
        aging_buckets = {
            "current": {"count": 0, "amount": 0},
            "1_30_days": {"count": 0, "amount": 0},
            "31_60_days": {"count": 0, "amount": 0},
            "61_90_days": {"count": 0, "amount": 0},
            "over_90_days": {"count": 0, "amount": 0},
        }

        customer_balances = {}

        for invoice in invoices:
            outstanding = invoice.total_amount - invoice.paid_amount
            days_overdue = (
                (as_of_date - invoice.due_date).days if invoice.due_date else 0
            )

            # Determine aging bucket
            if days_overdue <= 0:
                bucket = "current"
            elif days_overdue <= 30:
                bucket = "1_30_days"
            elif days_overdue <= 60:
                bucket = "31_60_days"
            elif days_overdue <= 90:
                bucket = "61_90_days"
            else:
                bucket = "over_90_days"

            aging_buckets[bucket]["count"] += 1
            aging_buckets[bucket]["amount"] += outstanding

            # Customer summary
            if invoice.customer_id not in customer_balances:
                customer_balances[invoice.customer_id] = {
                    "customer_name": invoice.customer.short_name,
                    "customer_code": invoice.customer.customer_code,
                    "total_outstanding": 0,
                    "invoices": [],
                }

            customer_balances[invoice.customer_id]["total_outstanding"] += outstanding
            customer_balances[invoice.customer_id]["invoices"].append(
                {
                    "invoice_number": invoice.invoice_number,
                    "invoice_date": invoice.invoice_date,
                    "due_date": invoice.due_date,
                    "total_amount": invoice.total_amount,
                    "paid_amount": invoice.paid_amount,
                    "outstanding": outstanding,
                    "days_overdue": days_overdue,
                }
            )

        # Sort customers by outstanding amount
        sorted_customers = sorted(
            customer_balances.items(),
            key=lambda x: x[1]["total_outstanding"],
            reverse=True,
        )

        return {
            "as_of_date": as_of_date,
            "total_outstanding": sum(b["amount"] for b in aging_buckets.values()),
            "aging_buckets": aging_buckets,
            "customer_details": [
                {"customer_id": cid, **details} for cid, details in sorted_customers
            ],
        }

    async def get_tax_report(self, period: str) -> Dict[str, Any]:
        """Get tax report for government filing"""
        year = int(period[:4])
        month = int(period[4:6])

        # Date range
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Query issued invoices
        query = select(Invoice).where(
            and_(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date,
                Invoice.status == InvoiceStatus.ISSUED,
            )
        )

        result = await self.db.execute(query)
        invoices = result.scalars().all()

        # Calculate tax by type
        tax_summary = {
            "taxable_sales": {"count": 0, "sales_amount": 0, "tax_amount": 0},
            "zero_rated": {"count": 0, "sales_amount": 0, "tax_amount": 0},
            "tax_exempt": {"count": 0, "sales_amount": 0, "tax_amount": 0},
        }

        for invoice in invoices:
            if invoice.tax_type == "1":  # Taxable
                category = "taxable_sales"
            elif invoice.tax_type == "2":  # Zero-rated
                category = "zero_rated"
            else:  # Tax exempt
                category = "tax_exempt"

            tax_summary[category]["count"] += 1
            tax_summary[category]["sales_amount"] += invoice.sales_amount
            tax_summary[category]["tax_amount"] += invoice.tax_amount

        # Total calculations
        total_sales = sum(cat["sales_amount"] for cat in tax_summary.values())
        total_tax = sum(cat["tax_amount"] for cat in tax_summary.values())

        return {
            "period": period,
            "reporting_entity": {
                "tax_id": "12345678",  # Would come from settings
                "name": "幸福氣股份有限公司",
            },
            "tax_summary": tax_summary,
            "total_sales": total_sales,
            "total_tax": total_tax,
            "invoice_count": len(invoices),
            "void_invoice_count": await self._get_void_count(start_date, end_date),
        }

    async def get_cash_flow_report(
        self, date_from: date, date_to: date
    ) -> Dict[str, Any]:
        """Get cash flow report"""
        # Query payments in period
        payment_query = select(Payment).where(
            and_(Payment.payment_date >= date_from, Payment.payment_date <= date_to)
        )

        payment_result = await self.db.execute(payment_query)
        payments = payment_result.scalars().all()

        # Cash inflows by method
        inflows_by_method = {}
        for payment in payments:
            method = payment.payment_method.value
            if method not in inflows_by_method:
                inflows_by_method[method] = {"count": 0, "amount": 0}
            inflows_by_method[method]["count"] += 1
            inflows_by_method[method]["amount"] += payment.amount

        # Daily cash flow
        daily_flow = {}
        current_date = date_from
        while current_date <= date_to:
            daily_payments = [p for p in payments if p.payment_date == current_date]
            daily_flow[current_date.isoformat()] = {
                "inflow": sum(p.amount for p in daily_payments),
                "count": len(daily_payments),
            }
            current_date += timedelta(days=1)

        return {
            "period": {"from": date_from, "to": date_to},
            "total_inflow": sum(p.amount for p in payments),
            "payment_count": len(payments),
            "inflows_by_method": inflows_by_method,
            "daily_cash_flow": daily_flow,
            "average_daily_inflow": sum(p.amount for p in payments)
            / ((date_to - date_from).days + 1),
        }

    async def get_customer_statement(
        self, customer_id: int, date_from: date, date_to: date
    ) -> Dict[str, Any]:
        """Get customer account statement"""
        # Get customer
        customer = await self.db.get(Customer, customer_id)
        if not customer:
            raise ValueError("Customer not found")

        # Get invoices in period
        invoice_query = (
            select(Invoice)
            .where(
                and_(
                    Invoice.customer_id == customer_id,
                    Invoice.invoice_date >= date_from,
                    Invoice.invoice_date <= date_to,
                    Invoice.status == InvoiceStatus.ISSUED,
                )
            )
            .order_by(Invoice.invoice_date)
        )

        invoice_result = await self.db.execute(invoice_query)
        invoices = invoice_result.scalars().all()

        # Get payments
        payment_query = (
            select(Payment)
            .join(Invoice)
            .where(
                and_(
                    Invoice.customer_id == customer_id,
                    Payment.payment_date >= date_from,
                    Payment.payment_date <= date_to,
                )
            )
            .order_by(Payment.payment_date)
        )

        payment_result = await self.db.execute(payment_query)
        payments = payment_result.scalars().all()

        # Build transaction list
        transactions = []

        # Add invoices
        for invoice in invoices:
            transactions.append(
                {
                    "date": invoice.invoice_date,
                    "type": "invoice",
                    "reference": invoice.invoice_number,
                    "description": f"發票 {invoice.invoice_number}",
                    "debit": invoice.total_amount,
                    "credit": 0,
                    "balance": 0,  # Will calculate running balance
                }
            )

        # Add payments
        for payment in payments:
            transactions.append(
                {
                    "date": payment.payment_date,
                    "type": "payment",
                    "reference": payment.payment_number,
                    "description": f"付款 {payment.payment_method.value}",
                    "debit": 0,
                    "credit": payment.amount,
                    "balance": 0,
                }
            )

        # Sort by date and calculate running balance
        transactions.sort(key=lambda x: x["date"])

        # Get opening balance
        opening_balance = await self._get_customer_balance_before_date(
            customer_id, date_from
        )

        running_balance = opening_balance
        for trans in transactions:
            running_balance += trans["debit"] - trans["credit"]
            trans["balance"] = running_balance

        return {
            "customer": {
                "id": customer_id,
                "code": customer.customer_code,
                "name": customer.short_name,
                "tax_id": customer.tax_id,
            },
            "period": {"from": date_from, "to": date_to},
            "opening_balance": opening_balance,
            "closing_balance": running_balance,
            "total_invoiced": sum(t["debit"] for t in transactions),
            "total_paid": sum(t["credit"] for t in transactions),
            "transactions": transactions,
        }

    async def generate_401_file(self, period: str) -> str:
        """Generate 401 file for tax filing"""
        # This would generate the actual 401 format file
        # For now, return a sample format
        tax_report = await self.get_tax_report(period)

        content = []
        content.append(f"401|{period}|12345678|幸福氣股份有限公司")
        content.append(f"SALES|{tax_report['total_sales']}")
        content.append(f"TAX|{tax_report['total_tax']}")

        return "\n".join(content)

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get key financial metrics for dashboard"""
        today = date.today()
        month_start = date(today.year, today.month, 1)

        # Current month revenue
        current_month_revenue = await self._get_period_revenue(month_start, today)

        # Outstanding receivables
        ar_report = await self.get_accounts_receivable_report(today)

        # Today's collections
        today_payments = await self._get_date_payments(today)

        return {
            "current_month_revenue": current_month_revenue,
            "outstanding_receivables": ar_report["total_outstanding"],
            "overdue_amount": sum(
                ar_report["aging_buckets"][bucket]["amount"]
                for bucket in ["1_30_days", "31_60_days", "61_90_days", "over_90_days"]
            ),
            "today_collections": sum(p.amount for p in today_payments),
            "collection_count_today": len(today_payments),
        }

    async def _get_void_count(self, start_date: date, end_date: date) -> int:
        """Get count of voided invoices in period"""
        query = select(func.count(Invoice.id)).where(
            and_(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date,
                Invoice.status == InvoiceStatus.VOID,
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_customer_balance_before_date(
        self, customer_id: int, before_date: date
    ) -> float:
        """Get customer balance before a specific date"""
        # Invoices before date
        invoice_query = select(func.sum(Invoice.total_amount)).where(
            and_(
                Invoice.customer_id == customer_id,
                Invoice.invoice_date < before_date,
                Invoice.status == InvoiceStatus.ISSUED,
            )
        )
        invoice_result = await self.db.execute(invoice_query)
        total_invoiced = invoice_result.scalar() or 0

        # Payments before date
        payment_query = (
            select(func.sum(Payment.amount))
            .join(Invoice)
            .where(
                and_(
                    Invoice.customer_id == customer_id,
                    Payment.payment_date < before_date,
                )
            )
        )
        payment_result = await self.db.execute(payment_query)
        total_paid = payment_result.scalar() or 0

        return total_invoiced - total_paid

    async def _get_period_revenue(self, start_date: date, end_date: date) -> float:
        """Get total revenue for a period"""
        query = select(func.sum(Invoice.total_amount)).where(
            and_(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date,
                Invoice.status == InvoiceStatus.ISSUED,
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _get_date_payments(self, payment_date: date) -> List[Payment]:
        """Get all payments for a specific date"""
        query = select(Payment).where(Payment.payment_date == payment_date)
        result = await self.db.execute(query)
        return result.scalars().all()
