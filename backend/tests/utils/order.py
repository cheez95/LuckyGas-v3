"""
Order test utilities
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.order import Order, OrderStatus, PaymentStatus


async def create_test_order(
    db: AsyncSession,
    customer_id: int,
    order_number: str = None,
    scheduled_date: datetime = None,
    status: OrderStatus = OrderStatus.PENDING,
    payment_status: PaymentStatus = PaymentStatus.UNPAID,
    total_amount: float = 1000.0,
    discount_amount: float = 0.0,
    final_amount: float = None,
    qty_20kg: int = 1,
    qty_16kg: int = 0,
    qty_50kg: int = 0,
    qty_10kg: int = 0,
    qty_4kg: int = 0,
    **kwargs
) -> Order:
    """Create a test order"""
    if order_number is None:
        timestamp = datetime.utcnow()
        order_number = f"TEST-{timestamp.strftime('%Y%m%d')}-{timestamp.microsecond:06d}"
    
    if scheduled_date is None:
        scheduled_date = datetime.utcnow()
    
    if final_amount is None:
        final_amount = total_amount - discount_amount
    
    order = Order(
        order_number=order_number,
        customer_id=customer_id,
        scheduled_date=scheduled_date,
        status=status,
        payment_status=payment_status,
        total_amount=total_amount,
        discount_amount=discount_amount,
        final_amount=final_amount,
        qty_20kg=qty_20kg,
        qty_16kg=qty_16kg,
        qty_50kg=qty_50kg,
        qty_10kg=qty_10kg,
        qty_4kg=qty_4kg,
        payment_method="現金",
        **kwargs
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order