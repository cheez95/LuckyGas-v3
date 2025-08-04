"""
E2E tests for credit limit functionality (Sprint 3)
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.user import User


@pytest.mark.asyncio
class TestCreditLimitFlow:
    """Test credit limit management end-to-end flow"""
    
    async def test_credit_limit_validation_flow(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer,
        db_session: AsyncSession
    ):
        """Test complete credit limit validation workflow"""
        # 1. Set up customer with credit limit
        test_customer.credit_limit = 10000.0  # NT$10,000
        test_customer.current_balance = 0.0
        await db_session.commit()
        
        # 2. Check initial credit status
        response = await authenticated_client.get(
            f"/api/v1/orders/credit/{test_customer.id}"
        )
        assert response.status_code == 200
        credit_info = response.json()
        assert credit_info['credit_limit'] == 10000.0
        assert credit_info['current_balance'] == 0.0
        assert credit_info['available_credit'] == 10000.0
        assert not credit_info['is_credit_blocked']
        
        # 3. Create order within credit limit
        order_data = {
            'customer_id': test_customer.id,
            'scheduled_date': '2025-08-01T10:00:00',
            'qty_50kg': 2,  # Assume NT$2500 each = NT$5000
            'delivery_address': '台北市信義區測試路123號',
            'payment_method': '月結'
        }
        
        response = await authenticated_client.post(
            "/api/v1/orders",
            json=order_data
        )
        assert response.status_code == 201
        order1 = response.json()
        
        # 4. Check updated credit after order
        response = await authenticated_client.get(
            f"/api/v1/orders/credit/{test_customer.id}"
        )
        credit_info = response.json()
        assert credit_info['current_balance'] == 5000.0
        assert credit_info['available_credit'] == 5000.0
        
        # 5. Try to create order exceeding credit limit
        large_order_data = {
            'customer_id': test_customer.id,
            'scheduled_date': '2025-08-02T10:00:00',
            'qty_50kg': 3,  # NT$7500 > available credit
            'delivery_address': '台北市信義區測試路456號',
            'payment_method': '月結'
        }
        
        response = await authenticated_client.post(
            "/api/v1/orders",
            json=large_order_data
        )
        assert response.status_code == 400
        error = response.json()
        assert "信用額度不足" in error['detail']
        
        # 6. Mark first order as paid
        response = await authenticated_client.put(
            f"/api/v1/orders/{order1['id']}/payment",
            json={"payment_status": PaymentStatus.PAID.value}
        )
        assert response.status_code == 200
        
        # 7. Check credit is restored
        response = await authenticated_client.get(
            f"/api/v1/orders/credit/{test_customer.id}"
        )
        credit_info = response.json()
        assert credit_info['current_balance'] == 0.0
        assert credit_info['available_credit'] == 10000.0
        
        # 8. Now the large order should succeed
        response = await authenticated_client.post(
            "/api/v1/orders",
            json=large_order_data
        )
        assert response.status_code == 201
    
    async def test_credit_block_flow(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer,
        db_session: AsyncSession
    ):
        """Test credit blocking and unblocking flow"""
        # Set up customer
        test_customer.credit_limit = 5000.0
        test_customer.is_credit_blocked = False
        await db_session.commit()
        
        # 1. Block customer credit
        response = await authenticated_client.post(
            f"/api/v1/orders/credit/{test_customer.id}/block",
            json={"reason": "逾期未付款"}
        )
        assert response.status_code == 200
        
        # 2. Try to create order with blocked credit
        order_data = {
            'customer_id': test_customer.id,
            'scheduled_date': '2025-08-01T10:00:00',
            'qty_20kg': 1,
            'delivery_address': '台北市大安區測試路789號',
            'payment_method': '月結'
        }
        
        response = await authenticated_client.post(
            "/api/v1/orders",
            json=order_data
        )
        assert response.status_code == 400
        assert "信用額度已被凍結" in response.json()['detail']
        
        # 3. Unblock credit
        response = await authenticated_client.post(
            f"/api/v1/orders/credit/{test_customer.id}/unblock",
            json={"reason": "已結清欠款"}
        )
        assert response.status_code == 200
        
        # 4. Order should now succeed
        response = await authenticated_client.post(
            "/api/v1/orders",
            json=order_data
        )
        assert response.status_code == 201
    
    async def test_manager_override_flow(
        self,
        admin_client: AsyncClient,
        test_customer: Customer,
        db_session: AsyncSession
    ):
        """Test manager override for credit limit"""
        # Set up customer with low credit
        test_customer.credit_limit = 1000.0
        test_customer.current_balance = 800.0  # Only NT$200 available
        await db_session.commit()
        
        # Large order that exceeds credit
        order_data = {
            'customer_id': test_customer.id,
            'scheduled_date': '2025-08-01T10:00:00',
            'qty_50kg': 2,  # NT$5000
            'delivery_address': '台北市中山區測試路101號',
            'payment_method': '月結',
            'skip_credit_check': True  # Manager override
        }
        
        # Admin can override credit check
        response = await admin_client.post(
            "/api/v1/orders",
            json=order_data
        )
        assert response.status_code == 201
        order = response.json()
        assert order['notes'] == "管理員覆蓋信用檢查"
    
    async def test_overdue_amount_tracking(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer,
        order_factory,
        db_session: AsyncSession
    ):
        """Test tracking of overdue amounts"""
        from datetime import datetime, timedelta

        # Create an old unpaid order (35 days ago)
        old_date = datetime.now() - timedelta(days=35)
        old_order = await order_factory(
            customer_id=test_customer.id,
            scheduled_date=old_date,
            status=OrderStatus.DELIVERED,
            payment_status=PaymentStatus.UNPAID,
            final_amount=3000.0
        )
        
        # Create a recent unpaid order (10 days ago)
        recent_date = datetime.now() - timedelta(days=10)
        recent_order = await order_factory(
            customer_id=test_customer.id,
            scheduled_date=recent_date,
            status=OrderStatus.DELIVERED,
            payment_status=PaymentStatus.UNPAID,
            final_amount=2000.0
        )
        
        # Check credit summary
        response = await authenticated_client.get(
            f"/api/v1/orders/credit/{test_customer.id}"
        )
        assert response.status_code == 200
        credit_info = response.json()
        
        assert credit_info['current_balance'] == 5000.0  # Total unpaid
        assert credit_info['overdue_amount'] == 3000.0   # Only old order is overdue
        assert credit_info['overdue_days'] == 35
    
    async def test_credit_limit_bulk_operations(
        self,
        authenticated_client: AsyncClient,
        customer_factory,
        db_session: AsyncSession
    ):
        """Test credit operations on multiple customers"""
        # Create multiple customers with different credit statuses
        customers = []
        for i in range(3):
            customer = await customer_factory(
                customer_code=f"CREDIT{i:03d}",
                short_name=f"信用客戶{i+1}",
                credit_limit=5000.0 * (i + 1),
                current_balance=1000.0 * i
            )
            customers.append(customer)
        
        # Bulk credit check
        customer_ids = [c.id for c in customers]
        response = await authenticated_client.post(
            "/api/v1/orders/credit/check-bulk",
            json={
                "customer_ids": customer_ids,
                "order_amount": 3000.0
            }
        )
        assert response.status_code == 200
        results = response.json()
        
        # Verify results
        assert len(results) == 3
        assert results[0]['can_order'] == True   # 5000 limit, 0 balance
        assert results[1]['can_order'] == True   # 10000 limit, 1000 balance
        assert results[2]['can_order'] == True   # 15000 limit, 2000 balance