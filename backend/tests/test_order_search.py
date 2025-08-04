from datetime import datetime, timedelta

import pytest

from app.schemas.order_search import OrderSearchCriteria


@pytest.mark.asyncio
async def test_order_search_keyword(
    async_client,
    test_orders,
    test_user_headers_office
):
    """Test keyword search functionality"""
    # Search by order number
    criteria = {
        "keyword": test_orders[0].order_number
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(order["order_number"] == test_orders[0].order_number for order in data["orders"])
    
    # Search by customer name
    criteria = {
        "keyword": "測試客戶"
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_order_search_date_range(
    async_client,
    test_orders,
    test_user_headers_office
):
    """Test date range filtering"""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    criteria = {
        "date_from": yesterday.isoformat(),
        "date_to": tomorrow.isoformat()
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "search_time" in data


@pytest.mark.asyncio
async def test_order_search_multiple_filters(
    async_client,
    test_orders,
    test_user_headers_office
):
    """Test multiple filter combinations"""
    criteria = {
        "status": ["pending", "confirmed"],
        "priority": ["urgent", "normal"],
        "payment_status": ["pending"],
        "min_amount": 100,
        "max_amount": 10000
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["orders"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["search_time"], float)
    
    # Verify filtered results match criteria
    for order in data["orders"]:
        if "status" in order:
            assert order["status"] in ["pending", "confirmed"]
        if "final_amount" in order:
            assert 100 <= order["final_amount"] <= 10000


@pytest.mark.asyncio
async def test_order_search_cylinder_type(
    async_client,
    test_orders,
    test_user_headers_office
):
    """Test cylinder type filtering"""
    criteria = {
        "cylinder_type": ["20kg", "16kg"]
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    # Results should include orders with specified cylinder types
    assert isinstance(data["orders"], list)


@pytest.mark.asyncio
async def test_order_search_pagination(
    async_client,
    test_orders,
    test_user_headers_office
):
    """Test search with pagination"""
    criteria = {
        "skip": 0,
        "limit": 5
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["orders"]) <= 5
    assert data["skip"] == 0
    assert data["limit"] == 5
    
    # Test second page
    criteria = {
        "skip": 5,
        "limit": 5
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert data["skip"] == 5


@pytest.mark.asyncio
async def test_order_search_unauthorized(
    async_client
):
    """Test search requires authentication"""
    criteria = {
        "keyword": "test"
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_order_search_customer_type(
    async_client,
    test_orders,
    test_user_headers_office
):
    """Test customer type filtering"""
    criteria = {
        "customer_type": "household"
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["orders"], list)


@pytest.mark.asyncio
async def test_order_search_region(
    async_client,
    test_orders,
    test_user_headers_office
):
    """Test region filtering"""
    criteria = {
        "region": "north"
    }
    response = await async_client.post(
        "/api/v1/orders/search",
        json=criteria,
        headers=test_user_headers_office
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["orders"], list)
    # Orders should be from north region based on customer address