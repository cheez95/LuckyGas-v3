"""
Full system integration tests using mock services
Tests the complete flow from API endpoints through services to database
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
import json
from unittest.mock import patch, AsyncMock

from app.main import app
from app.models.user import User, UserRole
from app.models.customer import Customer, CustomerType
from app.models.order import Order, OrderStatus
from app.models.route import Route, RouteStatus
from app.models.delivery import Delivery
from app.services.google_cloud.mock_routes_service import MockGoogleRoutesService
from app.services.google_cloud.mock_vertex_ai_service import MockVertexAIDemandPredictionService
from app.core.security import get_password_hash


class TestFullSystemIntegration:
    """Test complete system flows with all components integrated"""
    
    @pytest_asyncio.fixture
    async def test_data(self, db_session: AsyncSession):
        """Create test data for integration tests"""
        # Create test users
        admin = User(
            email="admin@test.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Test Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        driver = User(
            email="driver@test.com",
            hashed_password=get_password_hash("driver123"),
            full_name="Test Driver",
            role=UserRole.DRIVER,
            is_active=True
        )
        office_staff = User(
            email="office@test.com",
            hashed_password=get_password_hash("office123"),
            full_name="Test Office",
            role=UserRole.OFFICE_STAFF,
            is_active=True
        )
        
        db_session.add_all([admin, driver, office_staff])
        await db_session.commit()
        
        # Create test customers
        customer1 = Customer(
            customer_code="CUST001",
            name="測試客戶一",
            customer_type=CustomerType.BUSINESS,
            phone="0912345678",
            address="台北市信義區信義路五段7號",
            cylinder_qty_50kg=2,
            cylinder_qty_20kg=5,
            credit_limit=50000,
            current_balance=10000
        )
        customer2 = Customer(
            customer_code="CUST002",
            name="測試客戶二",
            customer_type=CustomerType.RESIDENTIAL,
            phone="0923456789",
            address="台北市大安區忠孝東路四段100號",
            cylinder_qty_20kg=3,
            cylinder_qty_16kg=2,
            credit_limit=30000,
            current_balance=5000
        )
        
        db_session.add_all([customer1, customer2])
        await db_session.commit()
        
        return {
            "admin": admin,
            "driver": driver,
            "office_staff": office_staff,
            "customers": [customer1, customer2]
        }
    
    @pytest_asyncio.fixture
    async def mock_services(self):
        """Patch Google services with mocks"""
        with patch("app.services.vertex_ai_service.VertexAIService", MockVertexAIDemandPredictionService), \
             patch("app.services.google_cloud.vertex_ai_service.VertexAIService", MockVertexAIDemandPredictionService), \
             patch("app.services.google_cloud.routes_service.GoogleRoutesService", MockGoogleRoutesService), \
             patch("app.services.dispatch.google_routes_service.GoogleRoutesService", MockGoogleRoutesService):
            yield
    
    @pytest_asyncio.fixture
    async def authenticated_client(self, client: AsyncClient, test_data):
        """Client with authentication token"""
        # Login as office staff
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "office@test.com", "password": "office123"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        client.headers["Authorization"] = f"Bearer {token}"
        return client
    
    @pytest.mark.asyncio
    async def test_complete_order_to_delivery_flow(
        self,
        authenticated_client: AsyncClient,
        test_data,
        mock_services,
        db_session: AsyncSession
    ):
        """Test complete flow from order creation to delivery confirmation"""
        customers = test_data["customers"]
        driver = test_data["driver"]
        
        # Step 1: Create orders
        order_data = {
            "customer_id": customers[0].id,
            "scheduled_date": (date.today() + timedelta(days=1)).isoformat(),
            "delivery_time_start": "09:00",
            "delivery_time_end": "12:00",
            "qty_50kg": 1,
            "qty_20kg": 2,
            "delivery_address": customers[0].address,
            "delivery_notes": "請按門鈴",
            "is_urgent": False
        }
        
        response = await authenticated_client.post("/api/v1/orders", json=order_data)
        assert response.status_code == 200
        order1 = response.json()
        
        # Create second order
        order_data["customer_id"] = customers[1].id
        order_data["delivery_address"] = customers[1].address
        response = await authenticated_client.post("/api/v1/orders", json=order_data)
        assert response.status_code == 200
        order2 = response.json()
        
        # Step 2: Generate predictions (using mock Vertex AI)
        response = await authenticated_client.post("/api/v1/predictions/generate")
        assert response.status_code == 200
        predictions = response.json()
        assert predictions["predictions_count"] > 0
        
        # Step 3: Create and optimize route
        route_data = {
            "name": f"Route {date.today()}",
            "scheduled_date": (date.today() + timedelta(days=1)).isoformat(),
            "driver_id": driver.id,
            "order_ids": [order1["id"], order2["id"]]
        }
        
        response = await authenticated_client.post("/api/v1/routes", json=route_data)
        assert response.status_code == 200
        route = response.json()
        
        # Step 4: Optimize route (using mock Routes API)
        response = await authenticated_client.post(f"/api/v1/routes/{route['id']}/optimize")
        assert response.status_code == 200
        optimized_route = response.json()
        assert optimized_route["total_distance"] > 0
        assert optimized_route["total_duration"] > 0
        
        # Step 5: Driver starts route
        # Login as driver
        driver_response = await authenticated_client.post(
            "/api/v1/auth/login",
            data={"username": "driver@test.com", "password": "driver123"}
        )
        driver_token = driver_response.json()["access_token"]
        authenticated_client.headers["Authorization"] = f"Bearer {driver_token}"
        
        # Get driver's routes
        response = await authenticated_client.get("/api/v1/driver/routes")
        assert response.status_code == 200
        driver_routes = response.json()
        assert len(driver_routes) > 0
        
        # Start route
        response = await authenticated_client.post(
            f"/api/v1/driver/routes/{route['id']}/start"
        )
        assert response.status_code == 200
        
        # Step 6: Complete deliveries
        # Get route deliveries
        response = await authenticated_client.get(
            f"/api/v1/driver/routes/{route['id']}/deliveries"
        )
        assert response.status_code == 200
        deliveries = response.json()
        
        # Complete first delivery
        delivery_data = {
            "recipient_name": "王先生",
            "recipient_signature": "base64_signature_data",
            "delivery_notes": "順利送達",
            "is_successful": True
        }
        
        response = await authenticated_client.post(
            f"/api/v1/driver/deliveries/{deliveries[0]['id']}/complete",
            json=delivery_data
        )
        assert response.status_code == 200
        
        # Verify order status updated
        await db_session.refresh(db_session.get(Order, order1["id"]))
        order = await db_session.get(Order, order1["id"])
        assert order.status == OrderStatus.DELIVERED
        
        # Step 7: Generate invoice for delivered order
        authenticated_client.headers["Authorization"] = f"Bearer {driver_response.json()['access_token']}"
        
        invoice_data = {
            "order_id": order1["id"],
            "invoice_type": "B2B",
            "buyer_tax_id": "12345678"
        }
        
        response = await authenticated_client.post("/api/v1/invoices", json=invoice_data)
        assert response.status_code == 200
        invoice = response.json()
        assert invoice["invoice_number"] is not None
        assert invoice["total_amount"] > 0
    
    @pytest.mark.asyncio
    async def test_emergency_order_dispatch(
        self,
        authenticated_client: AsyncClient,
        test_data,
        mock_services,
        db_session: AsyncSession
    ):
        """Test emergency order handling and dispatch"""
        customer = test_data["customers"][0]
        driver = test_data["driver"]
        
        # Create urgent order
        order_data = {
            "customer_id": customer.id,
            "scheduled_date": date.today().isoformat(),
            "delivery_time_start": "14:00",
            "delivery_time_end": "16:00",
            "qty_50kg": 2,
            "delivery_address": customer.address,
            "delivery_notes": "緊急！瓦斯用完了",
            "is_urgent": True
        }
        
        response = await authenticated_client.post("/api/v1/orders", json=order_data)
        assert response.status_code == 200
        urgent_order = response.json()
        assert urgent_order["is_urgent"] is True
        
        # Create emergency route
        route_data = {
            "name": f"Emergency Route {datetime.now()}",
            "scheduled_date": date.today().isoformat(),
            "driver_id": driver.id,
            "order_ids": [urgent_order["id"]],
            "is_emergency": True
        }
        
        response = await authenticated_client.post("/api/v1/routes", json=route_data)
        assert response.status_code == 200
        emergency_route = response.json()
        
        # Verify priority handling
        assert emergency_route["status"] == RouteStatus.ASSIGNED.value
        
        # Get dispatch dashboard data
        response = await authenticated_client.get("/api/v1/dispatch/dashboard")
        assert response.status_code == 200
        dashboard = response.json()
        assert dashboard["urgent_orders"] > 0
    
    @pytest.mark.asyncio
    async def test_financial_reporting_flow(
        self,
        authenticated_client: AsyncClient,
        test_data,
        mock_services,
        db_session: AsyncSession
    ):
        """Test financial reporting with delivered orders"""
        # Create and complete some orders first
        customer = test_data["customers"][0]
        
        # Create multiple orders
        for i in range(3):
            order_data = {
                "customer_id": customer.id,
                "scheduled_date": (date.today() - timedelta(days=i)).isoformat(),
                "delivery_time_start": "09:00",
                "delivery_time_end": "12:00",
                "qty_50kg": 1,
                "qty_20kg": i + 1,
                "delivery_address": customer.address,
                "total_amount": 1000 + (i * 500),
                "status": OrderStatus.DELIVERED.value
            }
            
            response = await authenticated_client.post("/api/v1/orders", json=order_data)
            assert response.status_code == 200
        
        # Generate financial reports
        response = await authenticated_client.get(
            "/api/v1/financial-reports/revenue-summary",
            params={
                "start_date": (date.today() - timedelta(days=7)).isoformat(),
                "end_date": date.today().isoformat()
            }
        )
        assert response.status_code == 200
        revenue_report = response.json()
        assert revenue_report["total_revenue"] > 0
        assert len(revenue_report["daily_revenue"]) > 0
        
        # Get customer statements
        response = await authenticated_client.get(
            f"/api/v1/financial-reports/customer-statement/{customer.id}"
        )
        assert response.status_code == 200
        statement = response.json()
        assert statement["customer"]["id"] == customer.id
        assert len(statement["transactions"]) > 0
    
    @pytest.mark.asyncio
    async def test_websocket_real_time_updates(
        self,
        authenticated_client: AsyncClient,
        test_data,
        mock_services
    ):
        """Test WebSocket real-time updates during order processing"""
        # This would require WebSocket test client
        # For now, test the WebSocket endpoints exist
        response = await authenticated_client.get("/api/v1/websocket/status")
        assert response.status_code == 200
        
        status = response.json()
        assert "connections" in status
        assert "uptime" in status


# Additional integration test for batch operations
@pytest.mark.asyncio
async def test_batch_order_import(
    authenticated_client: AsyncClient,
    test_data,
    mock_services,
    db_session: AsyncSession
):
    """Test batch order import functionality"""
    customers = test_data["customers"]
    
    # Prepare batch order data
    batch_orders = [
        {
            "customer_code": customers[0].customer_code,
            "scheduled_date": (date.today() + timedelta(days=1)).isoformat(),
            "qty_50kg": 1,
            "qty_20kg": 2
        },
        {
            "customer_code": customers[1].customer_code,
            "scheduled_date": (date.today() + timedelta(days=1)).isoformat(),
            "qty_20kg": 3,
            "qty_16kg": 1
        }
    ]
    
    response = await authenticated_client.post(
        "/api/v1/orders/batch-import",
        json={"orders": batch_orders}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success_count"] == 2
    assert result["error_count"] == 0