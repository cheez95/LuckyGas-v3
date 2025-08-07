#!/usr / bin / env python3
"""Seed test data for driver functionality testing"""

import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.customer import Customer
from app.models.gas_product import GasProduct
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.route import Route, RouteStatus
from app.models.route_delivery import DeliveryStatus, RouteDelivery
from app.models.user import User


async def seed_driver_test_data():
    """Create test routes and deliveries for driver testing"""
    # Create engine
    engine = create_async_engine(settings.DATABASE_URL)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get test driver and customers
        result = await session.execute(
            select(User).where(User.email == "driver@luckygas.com.tw")
        )
        driver = result.scalar_one_or_none()

        if not driver:
            print("Driver user not found. Please run init_test_users.py first.")
            return

        # Get some customers
        result = await session.execute(select(Customer).limit(10))
        customers = result.scalars().all()

        if not customers:
            print("No customers found. Creating test customers...")
            # Create test customers
            test_customers = [
                Customer(
                    customer_code=f"C{i:04d}",
                    name=f"測試客戶{i}",
                    phone=f"091234{i:04d}",
                    address=f"台北市大安區測試路{i}號",
                    district="大安區",
                    customer_type="residential",
                )
                for i in range(1, 11)
            ]
            session.add_all(test_customers)
            await session.commit()
            customers = test_customers

        # Get or create a product
        result = await session.execute(select(GasProduct).limit(1))
        product = result.scalar_one_or_none()

        if not product:
            print("No products found. Creating test product...")
            from app.models.gas_product import DeliveryMethod, ProductAttribute

            product = GasProduct(
                sku="GAS - C20 - R",
                name_zh="20公斤家用桶裝瓦斯",
                name_en="20kg Home Gas Cylinder",
                description="家用桶裝瓦斯",
                unit_price=800.0,
                delivery_method=DeliveryMethod.CYLINDER,
                size_kg=20,
                attribute=ProductAttribute.REGULAR,
                is_active=True,
                is_available=True,
            )
            session.add(product)
            await session.commit()

        # Create routes for today
        today = date.today()

        # Morning route
        morning_route = Route(
            route_number=f"RT{today.strftime('%Y % m % d')}-001",
            route_name="早班路線 - 大安信義區",
            scheduled_date=today,
            date=datetime.combine(today, datetime.min.time()),
            driver_id=driver.id,
            status=RouteStatus.IN_PROGRESS,
            area="大安信義區",
            total_stops=5,
            completed_stops=2,
            total_distance_km=25.0,
            estimated_duration_minutes=240,
            is_active=True,
        )
        session.add(morning_route)

        # Afternoon route
        afternoon_route = Route(
            route_number=f"RT{today.strftime('%Y % m % d')}-002",
            route_name="午班路線 - 士林北投區",
            scheduled_date=today,
            date=datetime.combine(today, datetime.min.time()),
            driver_id=driver.id,
            status=RouteStatus.PENDING,
            area="士林北投區",
            total_stops=7,
            completed_stops=0,
            total_distance_km=35.0,
            estimated_duration_minutes=300,
            is_active=True,
        )
        session.add(afternoon_route)

        await session.commit()

        # Create orders and route deliveries for morning route
        for i, customer in enumerate(customers[:5]):
            # Create order
            order = Order(
                order_number=f"ORD{today.strftime('%Y % m % d')}-{i + 1:03d}",
                customer_id=customer.id,
                order_date=datetime.utcnow(),
                delivery_date=datetime.combine(today, datetime.min.time()),
                status=OrderStatus.CONFIRMED if i >= 2 else OrderStatus.DELIVERED,
                total_amount=800,
                delivery_address=customer.address,
                notes=f"測試訂單 {i + 1}",
            )
            session.add(order)
            await session.flush()

            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                unit_price=800,
                subtotal=800,
            )
            session.add(order_item)

            # Create route delivery
            delivery_status = (
                DeliveryStatus.DELIVERED if i < 2 else DeliveryStatus.PENDING
            )
            route_delivery = RouteDelivery(
                route_id=morning_route.id,
                order_id=order.id,
                sequence=i + 1,
                status=delivery_status,
                estimated_arrival=datetime.utcnow() + timedelta(minutes=30 * i),
                delivered_at=(
                    datetime.utcnow() - timedelta(minutes=30) if i < 2 else None
                ),
                recipient_name=customer.name if i < 2 else None,
                notes="已交付給本人" if i < 2 else None,
            )
            session.add(route_delivery)

        # Create orders and route deliveries for afternoon route
        for i, customer in enumerate(customers[5:]):
            # Create order
            order = Order(
                order_number=f"ORD{today.strftime('%Y % m % d')}-{i + 6:03d}",
                customer_id=customer.id,
                order_date=datetime.utcnow(),
                delivery_date=datetime.combine(today, datetime.min.time()),
                status=OrderStatus.CONFIRMED,
                total_amount=800,
                delivery_address=customer.address,
                notes=f"測試訂單 {i + 6}",
            )
            session.add(order)
            await session.flush()

            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                unit_price=800,
                subtotal=800,
            )
            session.add(order_item)

            # Create route delivery
            route_delivery = RouteDelivery(
                route_id=afternoon_route.id,
                order_id=order.id,
                sequence=i + 1,
                status=DeliveryStatus.PENDING,
                estimated_arrival=datetime.utcnow()
                + timedelta(hours=4, minutes=30 * i),
            )
            session.add(route_delivery)

        await session.commit()

        print("Created test data:")
        print(f"- 2 routes for driver {driver.full_name}")
        print("- 5 deliveries for morning route (2 completed, 3 pending)")
        print(f"- {len(customers[5:])} deliveries for afternoon route (all pending)")

    await engine.dispose()
    print("\nDriver test data seeding completed!")


if __name__ == "__main__":
    asyncio.run(seed_driver_test_data())
