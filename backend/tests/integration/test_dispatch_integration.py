"""
Integration tests for dispatch operations
Tests route planning, optimization, and driver assignment workflows
"""
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.customer import Customer, CustomerType
from app.models.order import Order, OrderStatus
from app.models.route import Route, RouteStatus
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle


class TestDispatchIntegration:
    """Test dispatch operations with integrated components"""
    
    @pytest_asyncio.fixture
    async def dispatch_test_data(self, db_session: AsyncSession):
        """Create test data for dispatch operations"""
        # Create vehicles
        vehicle1 = Vehicle(
            license_plate="ABC-123",
            vehicle_type="truck",
            capacity_50kg=20,
            capacity_20kg=50,
            capacity_16kg=30,
            capacity_10kg=40,
            capacity_4kg=100,
            is_active=True
        )
        vehicle2 = Vehicle(
            license_plate="XYZ-789",
            vehicle_type="van",
            capacity_50kg=10,
            capacity_20kg=30,
            capacity_16kg=20,
            capacity_10kg=30,
            capacity_4kg=50,
            is_active=True
        )
        
        # Create drivers
        driver1 = User(
            email="driver1@test.com",
            hashed_password=get_password_hash("password"),
            full_name="司機一號",
            role=UserRole.DRIVER,
            is_active=True
        )
        driver2 = User(
            email="driver2@test.com",
            hashed_password=get_password_hash("password"),
            full_name="司機二號",
            role=UserRole.DRIVER,
            is_active=True
        )
        
        # Create manager
        manager = User(
            email="manager@test.com",
            hashed_password=get_password_hash("password"),
            full_name="經理",
            role=UserRole.MANAGER,
            is_active=True
        )
        
        db_session.add_all([vehicle1, vehicle2, driver1, driver2, manager])
        await db_session.commit()
        
        # Assign vehicles to drivers
        vehicle1.assigned_driver_id = driver1.id
        vehicle2.assigned_driver_id = driver2.id
        await db_session.commit()
        
        # Create customers across different areas
        customers = []
        areas = ["信義區", "大安區", "中山區", "松山區", "內湖區"]
        for i, area in enumerate(areas):
            customer = Customer(
                customer_code=f"AREA{i:03d}",
                name=f"{area}客戶{i+1}",
                customer_type=CustomerType.BUSINESS,
                phone=f"0912345{i:03d}",
                address=f"台北市{area}測試路{i+1}號",
                area=area,
                cylinder_qty_50kg=2,
                cylinder_qty_20kg=5,
                credit_limit=100000,
                current_balance=0
            )
            customers.append(customer)
        
        db_session.add_all(customers)
        await db_session.commit()
        
        return {
            "vehicles": [vehicle1, vehicle2],
            "drivers": [driver1, driver2],
            "manager": manager,
            "customers": customers
        }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_route_planning_and_optimization(
        self,
        client: AsyncClient,
        dispatch_test_data,
        mock_google_services,
        db_session: AsyncSession
    ):
        """Test complete route planning and optimization workflow"""
        data = dispatch_test_data
        
        # Login as manager
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "manager@test.com", "password": "password"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        
        # Create multiple orders for route planning
        order_ids = []
        for i, customer in enumerate(data["customers"]):
            order_data = {
                "customer_id": customer.id,
                "scheduled_date": (date.today() + timedelta(days=1)).isoformat(),
                "delivery_time_start": "09:00",
                "delivery_time_end": "17:00",
                "qty_50kg": 1 if i % 2 == 0 else 0,
                "qty_20kg": 2,
                "qty_16kg": 1,
                "delivery_address": customer.address,
                "delivery_notes": f"Order for {customer.area}"
            }
            
            response = await client.post("/api/v1/orders", json=order_data)
            assert response.status_code == 200
            order_ids.append(response.json()["id"])
        
        # Get unassigned orders
        response = await client.get(
            "/api/v1/dispatch/unassigned-orders",
            params={"date": (date.today() + timedelta(days=1)).isoformat()}
        )
        assert response.status_code == 200
        unassigned = response.json()
        assert len(unassigned) == len(order_ids)
        
        # Create optimized routes using VRP solver
        route_request = {
            "date": (date.today() + timedelta(days=1)).isoformat(),
            "order_ids": order_ids,
            "vehicle_ids": [v.id for v in data["vehicles"]],
            "optimization_params": {
                "time_windows": True,
                "capacity_constraints": True,
                "minimize_distance": True
            }
        }
        
        response = await client.post(
            "/api/v1/dispatch/optimize-routes",
            json=route_request
        )
        assert response.status_code == 200
        optimized_routes = response.json()
        
        # Verify optimization results
        assert len(optimized_routes["routes"]) <= len(data["vehicles"])
        total_orders_assigned = sum(
            len(route["order_ids"]) for route in optimized_routes["routes"]
        )
        assert total_orders_assigned == len(order_ids)
        
        # Assign routes to drivers
        for i, route_data in enumerate(optimized_routes["routes"]):
            assignment = {
                "driver_id": data["drivers"][i].id,
                "vehicle_id": data["vehicles"][i].id,
                "notes": f"Route {i+1} optimized"
            }
            
            response = await client.post(
                f"/api/v1/routes/{route_data['route_id']}/assign",
                json=assignment
            )
            assert response.status_code == 200
        
        # Verify dispatch dashboard
        response = await client.get("/api/v1/dispatch/dashboard")
        assert response.status_code == 200
        dashboard = response.json()
        assert dashboard["total_routes"] == len(optimized_routes["routes"])
        assert dashboard["assigned_routes"] == len(optimized_routes["routes"])
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_emergency_dispatch_workflow(
        self,
        client: AsyncClient,
        dispatch_test_data,
        mock_google_services,
        db_session: AsyncSession
    ):
        """Test emergency order dispatch and reassignment"""
        data = dispatch_test_data
        
        # Login as manager
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "manager@test.com", "password": "password"}
        )
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        
        # Create an existing route with orders
        regular_orders = []
        for customer in data["customers"][:3]:
            order_data = {
                "customer_id": customer.id,
                "scheduled_date": date.today().isoformat(),
                "delivery_time_start": "14:00",
                "delivery_time_end": "17:00",
                "qty_20kg": 2,
                "delivery_address": customer.address
            }
            response = await client.post("/api/v1/orders", json=order_data)
            regular_orders.append(response.json()["id"])
        
        # Create route for regular orders
        route_data = {
            "name": "Regular Route",
            "scheduled_date": date.today().isoformat(),
            "driver_id": data["drivers"][0].id,
            "vehicle_id": data["vehicles"][0].id,
            "order_ids": regular_orders
        }
        response = await client.post("/api/v1/routes", json=route_data)
        regular_route = response.json()
        
        # Create emergency order
        emergency_order_data = {
            "customer_id": data["customers"][-1].id,
            "scheduled_date": date.today().isoformat(),
            "delivery_time_start": "ASAP",
            "delivery_time_end": "15:00",
            "qty_50kg": 2,
            "delivery_address": data["customers"][-1].address,
            "delivery_notes": "緊急！瓦斯用完了",
            "is_urgent": True
        }
        response = await client.post("/api/v1/orders", json=emergency_order_data)
        emergency_order = response.json()
        
        # Dispatch emergency order
        dispatch_data = {
            "order_id": emergency_order["id"],
            "dispatch_strategy": "nearest_driver",
            "max_delay_minutes": 30
        }
        
        response = await client.post(
            "/api/v1/dispatch/emergency",
            json=dispatch_data
        )
        assert response.status_code == 200
        dispatch_result = response.json()
        
        # Verify emergency dispatch
        assert dispatch_result["success"] is True
        assert dispatch_result["assigned_driver_id"] is not None
        assert dispatch_result["estimated_arrival_time"] is not None
        
        # Check route was updated
        response = await client.get(f"/api/v1/routes/{regular_route['id']}")
        updated_route = response.json()
        assert emergency_order["id"] in [o["id"] for o in updated_route["orders"]]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_route_tracking_and_updates(
        self,
        client: AsyncClient,
        dispatch_test_data,
        mock_google_services,
        mock_websocket,
        db_session: AsyncSession
    ):
        """Test real-time route tracking and status updates"""
        data = dispatch_test_data
        driver = data["drivers"][0]
        
        # Create a route with orders
        orders = []
        for customer in data["customers"][:2]:
            order = Order(
                customer_id=customer.id,
                order_number=f"TEST{customer.id:04d}",
                scheduled_date=date.today(),
                qty_20kg=2,
                delivery_address=customer.address,
                status=OrderStatus.ASSIGNED
            )
            db_session.add(order)
            orders.append(order)
        
        await db_session.commit()
        
        route = Route(
            name="Test Route",
            scheduled_date=date.today(),
            driver_id=driver.id,
            vehicle_id=data["vehicles"][0].id,
            status=RouteStatus.ASSIGNED
        )
        db_session.add(route)
        await db_session.commit()
        
        # Add orders to route
        for order in orders:
            order.route_id = route.id
        await db_session.commit()
        
        # Login as driver
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": driver.email, "password": "password"}
        )
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        
        # Start route
        response = await client.post(f"/api/v1/driver/routes/{route.id}/start")
        assert response.status_code == 200
        
        # Verify WebSocket notification was sent
        mock_websocket.broadcast.assert_called()
        
        # Update location
        location_update = {
            "latitude": 25.033,
            "longitude": 121.565,
            "heading": 45,
            "speed": 30
        }
        response = await client.post(
            f"/api/v1/driver/routes/{route.id}/update-location",
            json=location_update
        )
        assert response.status_code == 200
        
        # Complete first delivery
        delivery_data = {
            "order_id": orders[0].id,
            "recipient_name": "王先生",
            "recipient_signature": "base64_signature",
            "delivery_notes": "順利送達"
        }
        response = await client.post(
            f"/api/v1/driver/deliveries/complete",
            json=delivery_data
        )
        assert response.status_code == 200
        
        # Verify order status updated
        await db_session.refresh(orders[0])
        assert orders[0].status == OrderStatus.DELIVERED
        
        # Get route progress
        response = await client.get(f"/api/v1/driver/routes/{route.id}/progress")
        assert response.status_code == 200
        progress = response.json()
        assert progress["completed_orders"] == 1
        assert progress["total_orders"] == 2
        assert progress["completion_percentage"] == 50