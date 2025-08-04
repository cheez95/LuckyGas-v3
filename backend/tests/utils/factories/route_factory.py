"""
Route factory for test data generation
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
import random
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import Route, RouteStop
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.models.vehicle import Vehicle
from tests.utils.factories.base import BaseFactory


class RouteFactory(BaseFactory):
    """Factory for creating Route test data"""

    model = Route

    async def get_default_data(self) -> Dict[str, Any]:
        """Get default route data"""
        return {
            "route_date": date.today(),
            "status": "pending",
            "total_distance_km": round(random.uniform(20, 100), 1),
            "total_duration_minutes": random.randint(60, 480),
            "optimization_savings_percentage": round(random.uniform(5, 25), 1),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

    async def create_with_stops(
        self, driver: User, vehicle: Vehicle, num_stops: int = 5, **kwargs
    ) -> Route:
        """Create a route with multiple stops"""
        # Create the route
        route_data = await self.build(**kwargs)
        route_data.update({"driver_id": driver.id, "vehicle_id": vehicle.id})

        route = await self.create(**route_data)

        # Create stops
        stop_factory = RouteStopFactory(self.session)
        stops = []

        base_time = datetime.combine(
            route.route_date, datetime.min.time().replace(hour=8)
        )

        for i in range(num_stops):
            # Create order for each stop
            from tests.utils.factories.order_factory import OrderFactory

            order_factory = OrderFactory(self.session)
            order = await order_factory.create(
                scheduled_date=route.route_date, status=OrderStatus.CONFIRMED
            )

            # Create stop
            stop = await stop_factory.create(
                route_id=route.id,
                order_id=order.id,
                sequence=i + 1,
                estimated_arrival=base_time + timedelta(minutes=30 * i),
                estimated_duration=15,
            )
            stops.append(stop)

        # Update route with stops
        route.stops = stops
        await self.session.commit()

        return route

    async def create_optimized_route(
        self,
        driver: User,
        vehicle: Vehicle,
        orders: List[Order],
        depot_lat: float = 25.0478,
        depot_lng: float = 121.5318,
        **kwargs,
    ) -> Route:
        """Create an optimized route from orders"""
        # Calculate route metrics based on orders
        total_distance = len(orders) * random.uniform(3, 8)  # km per stop
        total_duration = len(orders) * random.randint(15, 25)  # minutes per stop

        route_data = await self.build(**kwargs)
        route_data.update(
            {
                "driver_id": driver.id,
                "vehicle_id": vehicle.id,
                "total_distance_km": round(total_distance, 1),
                "total_duration_minutes": total_duration,
                "depot_latitude": depot_lat,
                "depot_longitude": depot_lng,
                "optimization_savings_percentage": round(random.uniform(10, 20), 1),
            }
        )

        route = await self.create(**route_data)

        # Create stops in optimized order
        stop_factory = RouteStopFactory(self.session)
        base_time = datetime.combine(
            route.route_date, datetime.min.time().replace(hour=8)
        )

        # Simulate optimization by sorting orders by location
        sorted_orders = sorted(
            orders, key=lambda o: (o.delivery_latitude or 0, o.delivery_longitude or 0)
        )

        for i, order in enumerate(sorted_orders):
            await stop_factory.create(
                route_id=route.id,
                order_id=order.id,
                sequence=i + 1,
                estimated_arrival=base_time + timedelta(minutes=20 * i),
                estimated_duration=15,
                distance_from_previous=round(random.uniform(2, 5), 1) if i > 0 else 0,
            )

            # Update order status
            order.status = OrderStatus.IN_DELIVERY
            self.session.add(order)

        await self.session.commit()
        return route


class RouteStopFactory(BaseFactory):
    """Factory for creating RouteStop test data"""

    model = RouteStop

    async def get_default_data(self) -> Dict[str, Any]:
        """Get default route stop data"""
        return {
            "status": "pending",
            "estimated_duration": 15,
            "distance_from_previous": round(random.uniform(1, 10), 1),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

    async def create_completed_stop(
        self, route_id: int, order_id: int, sequence: int, **kwargs
    ) -> RouteStop:
        """Create a completed stop with delivery details"""
        stop_data = await self.build(**kwargs)
        stop_data.update(
            {
                "route_id": route_id,
                "order_id": order_id,
                "sequence": sequence,
                "status": "completed",
                "actual_arrival": kwargs.get("estimated_arrival", datetime.now()),
                "actual_departure": kwargs.get("estimated_arrival", datetime.now())
                + timedelta(minutes=15),
                "actual_duration": 15,
                "delivery_notes": "已成功配送",
                "customer_signature": "signature_base64_data",
                "delivery_photo": "photo_base64_data",
            }
        )

        return await self.create(**stop_data)


class RouteTestDataGenerator:
    """Generate complex route test scenarios"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.route_factory = RouteFactory(session)
        self.stop_factory = RouteStopFactory(session)

    async def create_daily_routes(
        self, date: date, num_routes: int = 5, stops_per_route: int = 10
    ) -> List[Route]:
        """Create multiple routes for a specific date"""
        from tests.utils.factories.user_factory import UserFactory
        from tests.utils.factories.vehicle_factory import VehicleFactory

        user_factory = UserFactory(self.session)
        vehicle_factory = VehicleFactory(self.session)

        routes = []

        for i in range(num_routes):
            # Create driver and vehicle
            driver = await user_factory.create_driver(
                username=f"driver_{date.strftime('%Y%m%d')}_{i}",
                full_name=f"測試司機 {i+1}",
            )

            vehicle = await vehicle_factory.create(
                license_plate=f"TEST-{date.strftime('%Y%m%d')}-{i:03d}"
            )

            # Create route
            route = await self.route_factory.create_with_stops(
                driver=driver,
                vehicle=vehicle,
                num_stops=stops_per_route,
                route_date=date,
                status="completed" if date < date.today() else "pending",
            )

            routes.append(route)

        return routes

    async def create_route_with_adjustments(
        self,
        driver: User,
        vehicle: Vehicle,
        initial_stops: int = 5,
        adjustments: int = 2,
    ) -> Route:
        """Create a route that has been adjusted multiple times"""
        route = await self.route_factory.create_with_stops(
            driver=driver,
            vehicle=vehicle,
            num_stops=initial_stops,
            status="in_progress",
            adjustment_count=adjustments,
        )

        # Add adjustment history (would need separate model in real app)
        route.last_adjustment_time = datetime.now()
        route.last_adjustment_reason = "urgent_order_added"

        await self.session.commit()
        return route
