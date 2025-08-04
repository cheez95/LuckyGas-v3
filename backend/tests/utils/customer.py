"""
Customer test utilities
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


async def create_test_customer(
    db: AsyncSession,
    customer_code: str = "TEST001",
    short_name: str = "測試客戶",
    address: str = "台北市信義區測試路123號",
    credit_limit: float = 0.0,
    current_balance: float = 0.0,
    is_credit_blocked: bool = False,
    is_terminated: bool = False,
    **kwargs,
) -> Customer:
    """Create a test customer"""
    customer = Customer(
        customer_code=customer_code,
        short_name=short_name,
        address=address,
        credit_limit=credit_limit,
        current_balance=current_balance,
        is_credit_blocked=is_credit_blocked,
        is_terminated=is_terminated,
        phone="0912345678",
        area="台北市",
        customer_type="商業",
        **kwargs,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer
