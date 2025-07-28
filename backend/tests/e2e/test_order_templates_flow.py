"""
E2E tests for order templates functionality (Sprint 3)
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.order_template import OrderTemplate
from app.models.user import User


@pytest.mark.asyncio
class TestOrderTemplatesFlow:
    """Test order templates end-to-end flow"""
    
    async def test_template_lifecycle(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer
    ):
        """Test complete template creation, usage, and management flow"""
        # 1. Create a template
        template_data = {
            "template_name": "每月標準訂單",
            "template_code": "MONTHLY-STD",
            "description": "每月固定訂購的標準瓦斯組合",
            "customer_id": test_customer.id,
            "products": [
                {
                    "gas_product_id": 1,
                    "quantity": 2,
                    "unit_price": 2500,
                    "discount_percentage": 5,
                    "is_exchange": True,
                    "empty_received": 2
                },
                {
                    "gas_product_id": 2,
                    "quantity": 1,
                    "unit_price": 1200,
                    "discount_percentage": 0,
                    "is_exchange": True,
                    "empty_received": 1
                }
            ],
            "delivery_notes": "請放置於後門，並通知警衛",
            "priority": "normal",
            "payment_method": "月結",
            "is_recurring": True,
            "recurrence_pattern": "monthly",
            "recurrence_day": 15
        }
        
        response = await authenticated_client.post(
            "/api/v1/order-templates",
            json=template_data
        )
        assert response.status_code == 201
        template = response.json()
        template_id = template['id']
        
        # 2. List customer templates
        response = await authenticated_client.get(
            f"/api/v1/order-templates/customer/{test_customer.id}"
        )
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) >= 1
        assert any(t['id'] == template_id for t in templates)
        
        # 3. Create order from template
        response = await authenticated_client.post(
            f"/api/v1/order-templates/{template_id}/create-order",
            json={
                "scheduled_date": "2025-08-15T10:00:00",
                "delivery_address": test_customer.address,
                "additional_notes": "本月請早上送達"
            }
        )
        assert response.status_code == 201
        order = response.json()
        
        # Verify order matches template
        assert order['customer_id'] == test_customer.id
        assert order['qty_50kg'] == 2  # Assuming product 1 is 50kg
        assert order['qty_20kg'] == 1  # Assuming product 2 is 20kg
        assert "請放置於後門" in order['delivery_notes']
        assert "本月請早上送達" in order['delivery_notes']
        assert order['payment_method'] == "月結"
        
        # 4. Update template usage count
        response = await authenticated_client.get(
            f"/api/v1/order-templates/{template_id}"
        )
        template = response.json()
        assert template['times_used'] == 1
        assert template['last_used_at'] is not None
        
        # 5. Update template
        update_data = {
            "template_name": "每月標準訂單 - 更新版",
            "products": [
                {
                    "gas_product_id": 1,
                    "quantity": 3,  # Increased quantity
                    "unit_price": 2500,
                    "discount_percentage": 10,  # Better discount
                    "is_exchange": True,
                    "empty_received": 3
                }
            ]
        }
        
        response = await authenticated_client.put(
            f"/api/v1/order-templates/{template_id}",
            json=update_data
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated['template_name'] == update_data['template_name']
        assert len(updated['products']) == 1
        assert updated['products'][0]['quantity'] == 3
        
        # 6. Deactivate template
        response = await authenticated_client.put(
            f"/api/v1/order-templates/{template_id}/deactivate"
        )
        assert response.status_code == 200
        
        # 7. Verify deactivated template not in active list
        response = await authenticated_client.get(
            f"/api/v1/order-templates/customer/{test_customer.id}"
        )
        templates = response.json()
        active_template = next((t for t in templates if t['id'] == template_id), None)
        if active_template:
            assert not active_template['is_active']
    
    async def test_recurring_template_scheduling(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer
    ):
        """Test recurring template scheduling functionality"""
        # Create weekly recurring template
        template_data = {
            "template_name": "每週配送",
            "template_code": "WEEKLY-01",
            "customer_id": test_customer.id,
            "products": [
                {
                    "gas_product_id": 3,
                    "quantity": 1,
                    "unit_price": 800,
                    "is_exchange": True,
                    "empty_received": 1
                }
            ],
            "is_recurring": True,
            "recurrence_pattern": "weekly",
            "recurrence_days_of_week": [1, 4]  # Monday and Thursday
        }
        
        response = await authenticated_client.post(
            "/api/v1/order-templates",
            json=template_data
        )
        assert response.status_code == 201
        template = response.json()
        
        # Get next occurrence
        response = await authenticated_client.get(
            f"/api/v1/order-templates/{template['id']}/next-occurrence"
        )
        assert response.status_code == 200
        next_date = response.json()['next_date']
        
        # Verify next date is a Monday or Thursday
        next_datetime = datetime.fromisoformat(next_date.replace('Z', '+00:00'))
        assert next_datetime.weekday() in [0, 3]  # 0=Monday, 3=Thursday
    
    async def test_template_quick_select(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer,
        test_order_template: OrderTemplate
    ):
        """Test quick template selection in order form"""
        # Get templates for quick select
        response = await authenticated_client.get(
            f"/api/v1/order-templates/customer/{test_customer.id}/quick-select"
        )
        assert response.status_code == 200
        templates = response.json()
        
        # Should include frequently used templates
        assert len(templates) > 0
        template = templates[0]
        
        # Apply template to new order
        response = await authenticated_client.post(
            "/api/v1/orders/apply-template",
            json={
                "template_id": template['id'],
                "customer_id": test_customer.id,
                "scheduled_date": "2025-08-20T14:00:00"
            }
        )
        assert response.status_code == 200
        order_data = response.json()
        
        # Verify template data applied
        assert order_data['products'] == template['products']
        assert order_data['delivery_notes'] == template['delivery_notes']
        assert order_data['payment_method'] == template['payment_method']
    
    async def test_template_statistics(
        self,
        authenticated_client: AsyncClient,
        test_customer: Customer,
        test_order_template: OrderTemplate
    ):
        """Test template usage statistics"""
        # Create multiple orders from template
        for i in range(3):
            response = await authenticated_client.post(
                f"/api/v1/order-templates/{test_order_template.id}/create-order",
                json={
                    "scheduled_date": f"2025-08-{10+i}T10:00:00",
                    "delivery_address": test_customer.address
                }
            )
            assert response.status_code == 201
        
        # Get template statistics
        response = await authenticated_client.get(
            f"/api/v1/order-templates/{test_order_template.id}/statistics"
        )
        assert response.status_code == 200
        stats = response.json()
        
        assert stats['total_usage'] >= 3
        assert stats['average_order_value'] > 0
        assert 'usage_by_month' in stats
        assert 'most_common_delivery_time' in stats
    
    async def test_template_search_and_filter(
        self,
        authenticated_client: AsyncClient,
        customer_factory
    ):
        """Test template search and filtering capabilities"""
        # Create templates for different customers
        customers = []
        templates = []
        
        for i in range(3):
            customer = await customer_factory(
                customer_code=f"TEMP{i:03d}",
                short_name=f"模板客戶{i+1}"
            )
            customers.append(customer)
            
            # Create template
            response = await authenticated_client.post(
                "/api/v1/order-templates",
                json={
                    "template_name": f"模板{i+1}",
                    "template_code": f"TPL{i:03d}",
                    "customer_id": customer.id,
                    "products": [
                        {
                            "gas_product_id": 1,
                            "quantity": i + 1,
                            "unit_price": 2500
                        }
                    ],
                    "is_recurring": i % 2 == 0,
                    "recurrence_pattern": "monthly" if i % 2 == 0 else None
                }
            )
            assert response.status_code == 201
            templates.append(response.json())
        
        # Search templates
        response = await authenticated_client.get(
            "/api/v1/order-templates/search",
            params={
                "query": "模板",
                "is_recurring": True,
                "is_active": True
            }
        )
        assert response.status_code == 200
        results = response.json()
        
        # Should find recurring templates
        assert len(results) >= 1
        for result in results:
            assert result['is_recurring'] == True