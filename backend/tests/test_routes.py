"""
Tests for route endpoints
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.delivery import DeliveryRoute as Route, RouteStatus, RouteStop
from app.models.vehicle import Vehicle, VehicleType
from app.models.user import User


class TestRoutes:
    """Test route endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_route(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_driver: User
    ):
        """Test creating a new route"""
        # Create vehicle
        vehicle = Vehicle(
            plate_number="ABC-123",
            vehicle_type=VehicleType.TRUCK,
            capacity_kg=1000,
            is_active=True,
            is_available=True
        )
        db_session.add(vehicle)
        await db_session.commit()
        await db_session.refresh(vehicle)
        
        route_data = {
            "route_date": "2024-12-25",
            "area": "信義區",
            "driver_id": test_driver.id,
            "vehicle_id": vehicle.id,
            "stops": []
        }
        
        response = await client.post(
            "/api/v1/routes",
            json=route_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["route_date"] == route_data["route_date"]
        assert data["area"] == route_data["area"]
        assert data["driver_id"] == test_driver.id
        assert data["vehicle_id"] == vehicle.id
        assert data["status"] == RouteStatus.PLANNED.value
    
    @pytest.mark.asyncio
    async def test_create_route_with_stops(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_driver: User
    ):
        """Test creating a route with stops"""
        # Create customer and orders
        customer = Customer(
            customer_code="C001",
            short_name="測試客戶",
            invoice_title="測試公司",
            address="台北市信義區測試路123號",
            area="信義區"
        )
        db_session.add(customer)
        await db_session.flush()
        
        orders = []
        for i in range(3):
            order = Order(
                order_number=f"ORD-TEST-{i:03d}",
                customer_id=customer.id,
                scheduled_date=datetime.now().date(),
                status=OrderStatus.CONFIRMED,
                qty_50kg=1,
                total_amount=2500,
                final_amount=2500
            )
            orders.append(order)
        db_session.add_all(orders)
        
        # Create vehicle
        vehicle = Vehicle(
            plate_number="ABC-123",
            vehicle_type=VehicleType.TRUCK,
            capacity_kg=1000,
            is_active=True,
            is_available=True
        )
        db_session.add(vehicle)
        await db_session.commit()
        
        # Refresh to get IDs
        for order in orders:
            await db_session.refresh(order)
        await db_session.refresh(vehicle)
        
        route_data = {
            "route_date": "2024-12-25",
            "area": "信義區",
            "driver_id": test_driver.id,
            "vehicle_id": vehicle.id,
            "stops": [
                {
                    "order_id": orders[0].id,
                    "stop_sequence": 1,
                    "latitude": 25.0330,
                    "longitude": 121.5654,
                    "address": "台北市信義區測試路123號",
                    "estimated_arrival": "2024-12-25T09:00:00",
                    "estimated_duration_minutes": 15
                },
                {
                    "order_id": orders[1].id,
                    "stop_sequence": 2,
                    "latitude": 25.0340,
                    "longitude": 121.5664,
                    "address": "台北市信義區測試路456號",
                    "estimated_arrival": "2024-12-25T09:30:00",
                    "estimated_duration_minutes": 15
                }
            ]
        }
        
        response = await client.post(
            "/api/v1/routes",
            json=route_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_stops"] == 2
        
        # Verify orders are assigned
        for order in orders[:2]:
            await db_session.refresh(order)
            assert order.route_id == data["id"]
            assert order.driver_id == test_driver.id
            assert order.status == OrderStatus.ASSIGNED
    
    @pytest.mark.asyncio
    async def test_list_routes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_driver: User
    ):
        """Test listing routes with filters"""
        # Create routes
        today = datetime.now().date()
        routes = []
        for i in range(5):
            route = Route(
                route_number=f"R{today.strftime('%Y%m%d')}-{i:03d}",
                route_date=today + timedelta(days=i),
                area="信義區" if i % 2 == 0 else "大安區",
                driver_id=test_driver.id if i < 3 else None,
                status=RouteStatus.PLANNED if i < 2 else RouteStatus.IN_PROGRESS,
                total_stops=i + 1
            )
            routes.append(route)
        db_session.add_all(routes)
        await db_session.commit()
        
        # Test listing all routes
        response = await client.get(
            "/api/v1/routes",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5
        
        # Test with area filter
        response = await client.get(
            "/api/v1/routes",
            params={"area": "信義區"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(route["area"] == "信義區" for route in data)
        
        # Test with driver filter
        response = await client.get(
            "/api/v1/routes",
            params={"driver_id": test_driver.id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all(route["driver_id"] == test_driver.id for route in data)
        
        # Test with status filter
        response = await client.get(
            "/api/v1/routes",
            params={"status": RouteStatus.IN_PROGRESS.value},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(route["status"] == RouteStatus.IN_PROGRESS.value for route in data)
    
    @pytest.mark.asyncio
    async def test_get_route(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_driver: User
    ):
        """Test getting a specific route"""
        # Create route
        route = Route(
            route_number="R20241225-001",
            route_date=datetime.now().date(),
            area="信義區",
            driver_id=test_driver.id,
            status=RouteStatus.PLANNED,
            total_stops=5
        )
        db_session.add(route)
        await db_session.commit()
        await db_session.refresh(route)
        
        response = await client.get(
            f"/api/v1/routes/{route.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == route.id
        assert data["route_number"] == route.route_number
        assert data["driver_name"] is not None  # Should include driver name
    
    @pytest.mark.asyncio
    async def test_update_route(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_driver: User
    ):
        """Test updating a route"""
        # Create another driver
        driver2 = User(
            email="driver2@example.com",
            username="driver2",
            full_name="Driver Two",
            hashed_password="hashed",
            role="driver",
            is_active=True
        )
        db_session.add(driver2)
        
        # Create route
        route = Route(
            route_number="R20241225-001",
            route_date=datetime.now().date(),
            area="信義區",
            driver_id=test_driver.id,
            status=RouteStatus.PLANNED,
            total_stops=5
        )
        db_session.add(route)
        await db_session.commit()
        await db_session.refresh(route)
        await db_session.refresh(driver2)
        
        update_data = {
            "driver_id": driver2.id,
            "status": RouteStatus.IN_PROGRESS.value
        }
        
        response = await client.put(
            f"/api/v1/routes/{route.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["driver_id"] == driver2.id
        assert data["status"] == RouteStatus.IN_PROGRESS.value
        assert data["started_at"] is not None
    
    @pytest.mark.asyncio
    async def test_cancel_route(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_driver: User
    ):
        """Test cancelling a route"""
        # Create route
        route = Route(
            route_number="R20241225-001",
            route_date=datetime.now().date(),
            area="信義區",
            driver_id=test_driver.id,
            status=RouteStatus.PLANNED,
            total_stops=5
        )
        db_session.add(route)
        await db_session.commit()
        await db_session.refresh(route)
        
        response = await client.delete(
            f"/api/v1/routes/{route.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "路線已成功取消" in response.json()["message"]
        
        # Verify route is cancelled
        await db_session.refresh(route)
        assert route.status == RouteStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_optimize_route(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_driver: User
    ):
        """Test route optimization"""
        # Create route with stops
        route = Route(
            route_number="R20241225-001",
            route_date=datetime.now().date(),
            area="信義區",
            driver_id=test_driver.id,
            status=RouteStatus.PLANNED,
            total_stops=0
        )
        db_session.add(route)
        await db_session.flush()
        
        # Create stops with different latitudes
        stops = []
        for i in range(3):
            stop = RouteStop(
                route_id=route.id,
                order_id=i + 1,  # Dummy order IDs
                stop_sequence=i + 1,
                latitude=25.0330 + (i * 0.01),  # Different latitudes
                longitude=121.5654,
                address=f"台北市信義區測試路{i+1}號"
            )
            stops.append(stop)
        db_session.add_all(stops)
        
        route.total_stops = len(stops)
        await db_session.commit()
        await db_session.refresh(route)
        
        response = await client.post(
            f"/api/v1/routes/{route.id}/optimize",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["route_id"] == route.id
        assert data["optimization_score"] > 0
        assert data["optimized_distance_km"] > 0
        assert data["distance_saved_percent"] > 0
        assert len(data["optimized_stops"]) == 3
        
        # Verify route is marked as optimized
        await db_session.refresh(route)
        assert route.is_optimized is True
        assert route.status == RouteStatus.OPTIMIZED
    
    @pytest.mark.asyncio
    async def test_driver_only_sees_own_routes(
        self,
        client: AsyncClient,
        driver_auth_headers: dict,
        db_session: AsyncSession,
        test_driver: User
    ):
        """Test that drivers can only see their own routes"""
        # Create another driver
        driver2 = User(
            email="driver2@example.com",
            username="driver2",
            full_name="Driver Two",
            hashed_password="hashed",
            role="driver",
            is_active=True
        )
        db_session.add(driver2)
        await db_session.flush()
        
        # Create routes for different drivers
        route1 = Route(
            route_number="R20241225-001",
            route_date=datetime.now().date(),
            area="信義區",
            driver_id=test_driver.id,
            status=RouteStatus.PLANNED
        )
        route2 = Route(
            route_number="R20241225-002",
            route_date=datetime.now().date(),
            area="大安區",
            driver_id=driver2.id,
            status=RouteStatus.PLANNED
        )
        db_session.add(route1)
        db_session.add(route2)
        await db_session.commit()
        
        # Driver should only see their own routes
        response = await client.get(
            "/api/v1/routes",
            headers=driver_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["driver_id"] == test_driver.id
        
        # Driver should not be able to see other driver's route
        response = await client.get(
            f"/api/v1/routes/{route2.id}",
            headers=driver_auth_headers
        )
        assert response.status_code == 403
        assert "無權查看此路線" in response.json()["detail"]