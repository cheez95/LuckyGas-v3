from datetime import datetime, timedelta

import pytest

from app.schemas.order_template import (
    CreateOrderFromTemplate,
    OrderTemplateCreate,
    OrderTemplateUpdate,
)


@pytest.mark.asyncio
async def test_create_order_template(
    async_client, test_customer, test_user_headers_office
):
    """Test creating an order template"""
    template_data = {
        "template_name": "標準訂單",
        "description": "每月標準瓦斯訂單",
        "customer_id": test_customer.id,
        "products": [
            {
                "gas_product_id": 1,
                "quantity": 2,
                "unit_price": 800,
                "is_exchange": True,
                "empty_received": 2,
            }
        ],
        "delivery_notes": "請放置於後門",
        "priority": "normal",
        "payment_method": "cash",
        "is_recurring": True,
        "recurrence_pattern": "monthly",
        "recurrence_interval": 1,
    }

    response = await async_client.post(
        "/api/v1/order-templates", json=template_data, headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert data["template_name"] == template_data["template_name"]
    assert data["customer_id"] == test_customer.id
    assert data["is_recurring"] == True
    assert data["recurrence_pattern"] == "monthly"
    assert len(data["products"]) == 1
    assert data["times_used"] == 0
    assert data["is_active"] == True
    assert "template_code" in data
    assert "id" in data


@pytest.mark.asyncio
async def test_list_order_templates(
    async_client, test_customer, test_user_headers_office
):
    """Test listing order templates"""
    # Create some templates first
    for i in range(3):
        template_data = {
            "template_name": f"模板{i+1}",
            "customer_id": test_customer.id,
            "products": [{"gas_product_id": 1, "quantity": 1}],
            "is_recurring": i == 0,  # First one is recurring
        }
        await async_client.post(
            "/api/v1/order-templates",
            json=template_data,
            headers=test_user_headers_office,
        )

    # List all templates
    response = await async_client.get(
        "/api/v1/order-templates", headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert "total" in data
    assert data["total"] >= 3

    # Filter by customer
    response = await async_client.get(
        f"/api/v1/order-templates?customer_id={test_customer.id}",
        headers=test_user_headers_office,
    )
    assert response.status_code == 200
    data = response.json()
    assert all(t["customer_id"] == test_customer.id for t in data["templates"])

    # Filter by recurring
    response = await async_client.get(
        "/api/v1/order-templates?is_recurring=true", headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert all(t["is_recurring"] == True for t in data["templates"])


@pytest.mark.asyncio
async def test_get_order_template(
    async_client, test_order_template, test_user_headers_office
):
    """Test getting a specific order template"""
    response = await async_client.get(
        f"/api/v1/order-templates/{test_order_template.id}",
        headers=test_user_headers_office,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_order_template.id
    assert data["template_name"] == test_order_template.template_name
    assert "product_details" in data  # Should include enriched product info


@pytest.mark.asyncio
async def test_update_order_template(
    async_client, test_order_template, test_user_headers_office
):
    """Test updating an order template"""
    update_data = {
        "template_name": "更新的模板",
        "is_active": False,
        "priority": "urgent",
    }

    response = await async_client.put(
        f"/api/v1/order-templates/{test_order_template.id}",
        json=update_data,
        headers=test_user_headers_office,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["template_name"] == update_data["template_name"]
    assert data["is_active"] == False
    assert data["priority"] == "urgent"


@pytest.mark.asyncio
async def test_delete_order_template(
    async_client, test_order_template, test_user_headers_manager
):
    """Test deleting an order template (soft delete)"""
    response = await async_client.delete(
        f"/api/v1/order-templates/{test_order_template.id}",
        headers=test_user_headers_manager,
    )
    assert response.status_code == 200

    # Verify it's deactivated
    response = await async_client.get(
        f"/api/v1/order-templates/{test_order_template.id}",
        headers=test_user_headers_manager,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] == False


@pytest.mark.asyncio
async def test_create_order_from_template(
    async_client, test_order_template, test_user_headers_office
):
    """Test creating an order from a template"""
    request_data = {
        "template_id": test_order_template.id,
        "scheduled_date": (datetime.now() + timedelta(days=1)).isoformat(),
        "delivery_notes": "額外備註",
    }

    response = await async_client.post(
        "/api/v1/order-templates/create-order",
        json=request_data,
        headers=test_user_headers_office,
    )
    assert response.status_code == 200
    data = response.json()
    assert "order_number" in data
    assert data["customer_id"] == test_order_template.customer_id
    assert data["delivery_notes"] == request_data["delivery_notes"]
    assert len(data["order_items"]) == len(test_order_template.products)

    # Verify template usage was updated
    response = await async_client.get(
        f"/api/v1/order-templates/{test_order_template.id}",
        headers=test_user_headers_office,
    )
    template_data = response.json()
    assert template_data["times_used"] == test_order_template.times_used + 1
    assert template_data["last_used_at"] is not None


@pytest.mark.asyncio
async def test_get_customer_templates(
    async_client, test_customer, test_order_template, test_user_headers_office
):
    """Test getting templates for a specific customer"""
    response = await async_client.get(
        f"/api/v1/order-templates/customer/{test_customer.id}/templates",
        headers=test_user_headers_office,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(t["customer_id"] == test_customer.id for t in data)
    assert all(t["is_active"] == True for t in data)  # Default active_only=True


@pytest.mark.asyncio
async def test_weekly_recurring_template(
    async_client, test_customer, test_user_headers_office
):
    """Test creating a weekly recurring template with specific days"""
    template_data = {
        "template_name": "每週一三五配送",
        "customer_id": test_customer.id,
        "products": [{"gas_product_id": 1, "quantity": 1}],
        "is_recurring": True,
        "recurrence_pattern": "weekly",
        "recurrence_interval": 1,
        "recurrence_days": [1, 3, 5],  # Mon, Wed, Fri
    }

    response = await async_client.post(
        "/api/v1/order-templates", json=template_data, headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recurrence_pattern"] == "weekly"
    assert data["recurrence_days"] == [1, 3, 5]
    assert data["next_scheduled_date"] is not None


@pytest.mark.asyncio
async def test_template_permissions(
    async_client, test_order_template, test_user_headers_driver
):
    """Test that drivers cannot create/update/delete templates"""
    # Try to create
    response = await async_client.post(
        "/api/v1/order-templates",
        json={"template_name": "Test", "products": []},
        headers=test_user_headers_driver,
    )
    assert response.status_code == 403

    # Try to update
    response = await async_client.put(
        f"/api/v1/order-templates/{test_order_template.id}",
        json={"template_name": "Updated"},
        headers=test_user_headers_driver,
    )
    assert response.status_code == 403

    # Try to delete
    response = await async_client.delete(
        f"/api/v1/order-templates/{test_order_template.id}",
        headers=test_user_headers_driver,
    )
    assert response.status_code == 403

    # But can read
    response = await async_client.get(
        f"/api/v1/order-templates/{test_order_template.id}",
        headers=test_user_headers_driver,
    )
    assert response.status_code == 200
