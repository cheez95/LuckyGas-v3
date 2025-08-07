"""
Test credit limit functionality
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.order import PaymentStatus
from app.services.credit_service import CreditService
from tests.utils.auth import get_test_token
from tests.utils.customer import create_test_customer
from tests.utils.order import create_test_order

# Import payment test marker
from tests.conftest_payment import requires_payment


@requires_payment
@pytest.mark.asyncio
async def test_credit_limit_check_within_limit(db: AsyncSession):
    """Test credit check when order is within limit"""
    # Create customer with credit limit
    customer = await create_test_customer(
        db, customer_code="TEST001", credit_limit=10000.0, current_balance=2000.0
    )

    # Check credit for new order
    result = await CreditService.check_credit_limit(
        db=db, customer_id=customer.id, order_amount=5000.0
    )

    assert result["approved"]
    assert result["reason"] == "Within credit limit"
    assert result["details"]["available_credit"] == 8000.0  # 10000 - 2000


@requires_payment
@pytest.mark.asyncio
async def test_credit_limit_check_exceeds_limit(db: AsyncSession):
    """Test credit check when order exceeds limit"""
    # Create customer with credit limit
    customer = await create_test_customer(
        db, customer_code="TEST002", credit_limit=10000.0, current_balance=8000.0
    )

    # Check credit for new order that exceeds limit
    result = await CreditService.check_credit_limit(
        db=db, customer_id=customer.id, order_amount=5000.0
    )

    assert not result["approved"]
    assert result["reason"] == "Credit limit exceeded"
    assert result["details"]["available_credit"] == 2000.0  # 10000 - 8000
    assert result["details"]["exceeds_by"] == 3000.0  # 5000 - 2000


@requires_payment
@pytest.mark.asyncio
async def test_credit_limit_check_blocked_customer(db: AsyncSession):
    """Test credit check for blocked customer"""
    # Create customer with blocked credit
    customer = await create_test_customer(
        db, customer_code="TEST003", credit_limit=10000.0, is_credit_blocked=True
    )

    # Check credit for blocked customer
    result = await CreditService.check_credit_limit(
        db=db, customer_id=customer.id, order_amount=1000.0
    )

    assert not result["approved"]
    assert result["reason"] == "Customer credit is blocked"


@requires_payment
@pytest.mark.asyncio
async def test_credit_limit_check_manager_override(db: AsyncSession):
    """Test credit check with manager override"""
    # Create customer with credit limit exceeded
    customer = await create_test_customer(
        db, customer_code="TEST004", credit_limit=10000.0, current_balance=9500.0
    )

    # Check credit with skip_check flag (manager override)
    result = await CreditService.check_credit_limit(
        db=db, customer_id=customer.id, order_amount=5000.0, skip_check=True
    )

    assert result["approved"]
    assert result["reason"] == "Manager override"


@requires_payment
@pytest.mark.asyncio
async def test_order_creation_with_credit_check(
    async_client: AsyncClient, db: AsyncSession
):
    """Test order creation API with credit limit checking"""
    # Get auth token for office staff
    token = await get_test_token(async_client, "office_staff")
    headers = {"Authorization": f"Bearer {token}"}

    # Create customer with limited credit
    customer = await create_test_customer(
        db, customer_code="TEST005", credit_limit=5000.0, current_balance=4000.0
    )

    # Try to create order that exceeds credit limit
    order_data = {
        "customer_id": customer.id,
        "scheduled_date": "2025 - 07 - 30T09:00:00",
        "qty_20kg": 2,
        "qty_16kg": 0,
        "qty_50kg": 0,
        "qty_10kg": 0,
        "qty_4kg": 0,
        "is_urgent": False,
        "payment_method": "現金",
        "delivery_notes": "Test order",
    }

    response = await async_client.post(
        f"{settings.API_V1_STR}/orders", json=order_data, headers=headers
    )

    assert response.status_code == 400
    data = response.json()
    assert "信用額度檢查失敗" in data["detail"]
    assert "可用額度: NT$1, 000" in data["detail"]


@requires_payment
@pytest.mark.asyncio
async def test_order_creation_with_super_admin_override(
    async_client: AsyncClient, db: AsyncSession
):
    """Test order creation with super admin credit override"""
    # Get auth token for super admin
    token = await get_test_token(async_client, "super_admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Create customer with exceeded credit
    customer = await create_test_customer(
        db, customer_code="TEST006", credit_limit=5000.0, current_balance=4900.0
    )

    # Create order that would normally exceed credit limit
    order_data = {
        "customer_id": customer.id,
        "scheduled_date": "2025 - 07 - 30T09:00:00",
        "qty_20kg": 2,
        "qty_16kg": 0,
        "qty_50kg": 0,
        "qty_10kg": 0,
        "qty_4kg": 0,
        "is_urgent": False,
        "payment_method": "現金",
        "delivery_notes": "Super admin override test",
    }

    response = await async_client.post(
        f"{settings.API_V1_STR}/orders", json=order_data, headers=headers
    )

    # Super admin should be able to create order regardless of credit limit
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["customer_id"] == customer.id


@requires_payment
@pytest.mark.asyncio
async def test_get_credit_summary(async_client: AsyncClient, db: AsyncSession):
    """Test getting customer credit summary"""
    # Get auth token
    token = await get_test_token(async_client, "office_staff")
    headers = {"Authorization": f"Bearer {token}"}

    # Create customer with some unpaid orders
    customer = await create_test_customer(
        db, customer_code="TEST007", credit_limit=20000.0
    )

    # Create some unpaid orders
    await create_test_order(
        db,
        customer_id=customer.id,
        total_amount=5000.0,
        payment_status=PaymentStatus.UNPAID,
    )

    await create_test_order(
        db,
        customer_id=customer.id,
        total_amount=3000.0,
        payment_status=PaymentStatus.UNPAID,
    )

    # Get credit summary
    response = await async_client.get(
        f"{settings.API_V1_STR}/orders / credit/{customer.id}", headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["credit_limit"] == 20000.0
    assert data["current_balance"] == 8000.0  # 5000 + 3000
    assert data["available_credit"] == 12000.0  # 20000 - 8000
    assert data["credit_utilization"] == 40.0  # (8000 / 20000) * 100


@requires_payment
@pytest.mark.asyncio
async def test_block_unblock_credit(async_client: AsyncClient, db: AsyncSession):
    """Test blocking and unblocking customer credit"""
    # Get auth token for manager
    token = await get_test_token(async_client, "manager")
    headers = {"Authorization": f"Bearer {token}"}

    # Create customer
    customer = await create_test_customer(
        db, customer_code="TEST008", credit_limit=10000.0
    )

    # Block credit
    response = await async_client.post(
        f"{settings.API_V1_STR}/orders / credit/{customer.id}/block",
        params={"reason": "Payment overdue 60 days"},
        headers=headers,
    )

    assert response.status_code == 200

    # Verify customer is blocked
    await db.refresh(customer)
    assert customer.is_credit_blocked

    # Unblock credit
    response = await async_client.post(
        f"{settings.API_V1_STR}/orders / credit/{customer.id}/unblock",
        params={"reason": "Payment received"},
        headers=headers,
    )

    assert response.status_code == 200

    # Verify customer is unblocked
    await db.refresh(customer)
    assert not customer.is_credit_blocked
