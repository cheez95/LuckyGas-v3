"""
Payment management API endpoints
"""
from typing import List, Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.api.deps import get_current_user
from app.models.user import User
from app.models.invoice import Invoice, InvoicePaymentStatus, Payment, PaymentMethod
from app.schemas.payment import (
    PaymentCreate, PaymentUpdate, PaymentResponse,
    PaymentSearchParams, PaymentStats, PaymentVerification
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Record a payment for an invoice"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限記錄付款")
    
    # Verify invoice exists
    invoice = await db.get(Invoice, payment_data.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="發票不存在")
    
    # Check if invoice can receive payment
    if invoice.status != "issued":
        raise HTTPException(status_code=400, detail="只有已開立發票可以記錄付款")
    
    if invoice.payment_status == InvoicePaymentStatus.PAID:
        raise HTTPException(status_code=400, detail="此發票已完全付清")
    
    # Check if payment amount is valid
    remaining_amount = invoice.total_amount - invoice.paid_amount
    if payment_data.amount > remaining_amount:
        raise HTTPException(
            status_code=400,
            detail=f"付款金額超過未付餘額 (餘額: {remaining_amount})"
        )
    
    # Create payment using service
    service = PaymentService(db)
    payment = await service.create_payment(
        payment_data=payment_data,
        created_by=current_user.id
    )
    
    return payment


@router.get("/", response_model=List[PaymentResponse])
async def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    invoice_id: Optional[int] = None,
    payment_method: Optional[PaymentMethod] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    is_verified: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Get list of payments with filtering"""
    query = select(Payment).options(
        selectinload(Payment.invoice)
    )
    
    # Apply filters
    filters = []
    
    if invoice_id:
        filters.append(Payment.invoice_id == invoice_id)
    
    if payment_method:
        filters.append(Payment.payment_method == payment_method)
    
    if date_from:
        filters.append(Payment.payment_date >= date_from)
    
    if date_to:
        filters.append(Payment.payment_date <= date_to)
    
    if is_verified is not None:
        filters.append(Payment.is_verified == is_verified)
    
    if search:
        # Search in payment number or reference
        filters.append(
            or_(
                Payment.payment_number.ilike(f"%{search}%"),
                Payment.reference_number.ilike(f"%{search}%")
            )
        )
    
    if filters:
        query = query.where(and_(*filters))
    
    # Order by date descending
    query = query.order_by(desc(Payment.payment_date), desc(Payment.id))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    payments = result.scalars().all()
    
    return payments


@router.get("/unverified", response_model=List[PaymentResponse])
async def get_unverified_payments(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Get all unverified payments for reconciliation"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看未核對付款")
    
    query = select(Payment).where(
        Payment.is_verified == False
    ).options(
        selectinload(Payment.invoice)
    ).order_by(Payment.payment_date)
    
    result = await db.execute(query)
    payments = result.scalars().all()
    
    return payments


@router.get("/stats", response_model=PaymentStats)
async def get_payment_stats(
    period: str = Query(..., pattern="^\\d{6}$", description="Period in YYYYMM format"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Get payment statistics for a period"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限查看統計資料")
    
    service = PaymentService(db)
    stats = await service.get_period_stats(period)
    
    return stats


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Get single payment details"""
    payment = await db.get(Payment, payment_id, options=[
        selectinload(Payment.invoice)
    ])
    
    if not payment:
        raise HTTPException(status_code=404, detail="付款記錄不存在")
    
    return payment


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_update: PaymentUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Update payment details (only unverified payments)"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限更新付款")
    
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="付款記錄不存在")
    
    # Only unverified payments can be edited
    if payment.is_verified and current_user.role != "super_admin":
        raise HTTPException(status_code=400, detail="已核對的付款無法修改")
    
    service = PaymentService(db)
    updated_payment = await service.update_payment(
        payment_id=payment_id,
        payment_update=payment_update
    )
    
    return updated_payment


@router.post("/{payment_id}/verify", response_model=PaymentResponse)
async def verify_payment(
    payment_id: int,
    verification_data: PaymentVerification,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Verify a payment for accounting reconciliation"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限核對付款")
    
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="付款記錄不存在")
    
    if payment.is_verified:
        raise HTTPException(status_code=400, detail="此付款已經核對")
    
    service = PaymentService(db)
    verified_payment = await service.verify_payment(
        payment_id=payment_id,
        verified_by=current_user.id,
        notes=verification_data.notes
    )
    
    return verified_payment


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Delete a payment (only unverified payments)"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限刪除付款")
    
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="付款記錄不存在")
    
    if payment.is_verified:
        raise HTTPException(status_code=400, detail="已核對的付款無法刪除")
    
    service = PaymentService(db)
    await service.delete_payment(payment_id)
    
    return {"message": "付款記錄已刪除"}


@router.post("/reconcile", response_model=dict)
async def reconcile_payments(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Reconcile payments for a date range"""
    if current_user.role not in ["super_admin", "manager"]:
        raise HTTPException(status_code=403, detail="沒有權限執行對帳")
    
    service = PaymentService(db)
    result = await service.reconcile_payments(
        date_from=date_from,
        date_to=date_to
    )
    
    return result


@router.get("/reports/daily-summary")
async def get_daily_payment_summary(
    date: date = Query(...),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Get daily payment summary report"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限查看報表")
    
    service = PaymentService(db)
    summary = await service.get_daily_summary(date)
    
    return summary


@router.get("/reports/customer-balance")
async def get_customer_balance_report(
    customer_id: Optional[int] = None,
    as_of_date: date = Query(default=date.today()),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Get customer balance report"""
    if current_user.role not in ["super_admin", "manager", "office_staff"]:
        raise HTTPException(status_code=403, detail="沒有權限查看報表")
    
    service = PaymentService(db)
    
    if customer_id:
        # Single customer balance
        balance = await service.get_customer_balance(customer_id, as_of_date)
        return {"customer_id": customer_id, "balance": balance, "as_of": as_of_date}
    else:
        # All customers with outstanding balance
        balances = await service.get_all_customer_balances(as_of_date)
        return {"balances": balances, "as_of": as_of_date}