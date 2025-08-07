"""
Test Data Initialization Script for Lucky Gas v3
This script seeds the test database with comprehensive sample data
"""

import asyncio
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, engine, get_db
from app.core.security import get_password_hash
from app.models import (
    Customer,
    CustomerInventory,
    DeliveryHistory,
    DeliveryHistoryItem,
    GasProduct,
    Invoice,
    Notification,
    Order,
    OrderItem,
    OrderTemplate,
    Route,
    RouteDelivery,
    User,
    Vehicle,
)
from app.schemas.user import UserRole

# Taiwan - specific test data
TAIWAN_CITIES = [
    "台北市",
    "新北市",
    "桃園市",
    "台中市",
    "台南市",
    "高雄市",
    "基隆市",
    "新竹市",
    "嘉義市",
    "新竹縣",
    "苗栗縣",
    "彰化縣",
    "南投縣",
    "雲林縣",
    "嘉義縣",
    "屏東縣",
    "宜蘭縣",
    "花蓮縣",
    "台東縣",
    "澎湖縣",
    "金門縣",
    "連江縣",
]

TAIWAN_DISTRICTS = {
    "台北市": [
        "中正區",
        "大同區",
        "中山區",
        "松山區",
        "大安區",
        "萬華區",
        "信義區",
        "士林區",
        "北投區",
        "內湖區",
        "南港區",
        "文山區",
    ],
    "新北市": [
        "板橋區",
        "三重區",
        "中和區",
        "永和區",
        "新莊區",
        "新店區",
        "樹林區",
        "鶯歌區",
        "三峽區",
        "淡水區",
        "汐止區",
        "瑞芳區",
    ],
    "高雄市": [
        "新興區",
        "前金區",
        "苓雅區",
        "鹽埕區",
        "鼓山區",
        "旗津區",
        "前鎮區",
        "三民區",
        "楠梓區",
        "小港區",
        "左營區",
        "仁武區",
    ],
}

TAIWAN_STREETS = [
    "中山路",
    "中正路",
    "民生路",
    "民權路",
    "復興路",
    "和平路",
    "信義路",
    "仁愛路",
    "忠孝路",
    "光復路",
    "建國路",
    "南京路",
]

CUSTOMER_TYPES = ["residential", "restaurant", "commercial", "industrial"]
ORDER_STATUSES = ["pending", "confirmed", "in_delivery", "delivered", "cancelled"]
ROUTE_STATUSES = ["draft", "planned", "in_progress", "completed"]
PAYMENT_METHODS = ["cash", "transfer", "credit", "monthly"]


class TestDataGenerator:
    """Generate realistic test data for Lucky Gas system"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = []
        self.customers = []
        self.products = []
        self.vehicles = []
        self.orders = []
        self.routes = []

    async def clean_database(self):
        """Clean all existing test data"""
        print("🧹 Cleaning existing test data...")

        # Delete in correct order to respect foreign keys
        tables_to_clean = [
            DeliveryHistoryItem,
            DeliveryHistory,
            Invoice,
            Notification,
            RouteDelivery,
            Route,
            OrderItem,
            Order,
            OrderTemplate,
            CustomerInventory,
            Customer,
            Vehicle,
            GasProduct,
            User,
        ]

        for table in tables_to_clean:
            result = await self.db.execute(select(table))
            entities = result.scalars().all()
            for entity in entities:
                await self.db.delete(entity)

        await self.db.commit()
        print("✅ Database cleaned")

    async def create_users(self):
        """Create test users with different roles"""
        print("👥 Creating test users...")

        users_data = [
            # Super Admin
            {
                "email": "admin@test.luckygas.tw",
                "full_name": "系統管理員",
                "password": "TestAdmin123!",
                "role": UserRole.SUPER_ADMIN,
                "is_active": True,
                "phone": "0912345678",
            },
            # Managers
            {
                "email": "manager1@test.luckygas.tw",
                "full_name": "陳經理",
                "password": "Manager123!",
                "role": UserRole.MANAGER,
                "is_active": True,
                "phone": "0923456789",
            },
            {
                "email": "manager2@test.luckygas.tw",
                "full_name": "林經理",
                "password": "Manager123!",
                "role": UserRole.MANAGER,
                "is_active": True,
                "phone": "0934567890",
            },
            # Office Staff
            {
                "email": "staff1@test.luckygas.tw",
                "full_name": "王小姐",
                "password": "Staff123!",
                "role": UserRole.OFFICE_STAFF,
                "is_active": True,
                "phone": "0945678901",
            },
            {
                "email": "staff2@test.luckygas.tw",
                "full_name": "李小姐",
                "password": "Staff123!",
                "role": UserRole.OFFICE_STAFF,
                "is_active": True,
                "phone": "0956789012",
            },
            # Drivers
            *[
                {
                    "email": f"driver{i}@test.luckygas.tw",
                    "full_name": f"司機{i}號",
                    "password": "Driver123!",
                    "role": UserRole.DRIVER,
                    "is_active": True,
                    "phone": f"096789{i:04d}",
                }
                for i in range(1, 11)
            ],
            # Customer Service
            {
                "email": "service@test.luckygas.tw",
                "full_name": "客服人員",
                "password": "Service123!",
                "role": UserRole.CUSTOMER_SERVICE,
                "is_active": True,
                "phone": "0978901234",
            },
        ]

        for user_data in users_data:
            user = User(
                email=user_data["email"],
                full_name=user_data["full_name"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                is_active=user_data["is_active"],
                phone=user_data["phone"],
            )
            self.db.add(user)
            self.users.append(user)

        await self.db.commit()
        print(f"✅ Created {len(self.users)} users")

    async def create_gas_products(self):
        """Create gas product catalog"""
        print("🔥 Creating gas products...")

        products_data = [
            {
                "name": "16公斤桶裝瓦斯",
                "code": "GAS - 16KG",
                "price": 800,
                "weight": 16,
            },
            {
                "name": "20公斤桶裝瓦斯",
                "code": "GAS - 20KG",
                "price": 1000,
                "weight": 20,
            },
            {
                "name": "50公斤桶裝瓦斯",
                "code": "GAS - 50KG",
                "price": 2500,
                "weight": 50,
            },
            {"name": "4公斤桶裝瓦斯", "code": "GAS - 4KG", "price": 200, "weight": 4},
            {
                "name": "瓦斯爐具 - 單口",
                "code": "STOVE - 1",
                "price": 1500,
                "weight": 5,
            },
            {
                "name": "瓦斯爐具 - 雙口",
                "code": "STOVE - 2",
                "price": 2500,
                "weight": 8,
            },
            {"name": "調節器", "code": "REGULATOR", "price": 300, "weight": 0.5},
            {"name": "瓦斯管", "code": "HOSE", "price": 200, "weight": 0.3},
        ]

        for prod_data in products_data:
            product = GasProduct(
                name=prod_data["name"],
                code=prod_data["code"],
                price=prod_data["price"],
                weight_kg=prod_data["weight"],
                is_active=True,
                stock_quantity=random.randint(50, 200),
            )
            self.db.add(product)
            self.products.append(product)

        await self.db.commit()
        print(f"✅ Created {len(self.products)} products")

    async def create_vehicles(self):
        """Create test vehicles"""
        print("🚚 Creating vehicles...")

        vehicles_data = [
            {
                "license_plate": "ABC - 1234",
                "capacity_kg": 1000,
                "vehicle_type": "truck",
            },
            {
                "license_plate": "DEF - 5678",
                "capacity_kg": 1500,
                "vehicle_type": "truck",
            },
            {"license_plate": "GHI - 9012", "capacity_kg": 800, "vehicle_type": "van"},
            {
                "license_plate": "JKL - 3456",
                "capacity_kg": 1200,
                "vehicle_type": "truck",
            },
            {
                "license_plate": "MNO - 7890",
                "capacity_kg": 1000,
                "vehicle_type": "truck",
            },
            {"license_plate": "PQR - 2345", "capacity_kg": 600, "vehicle_type": "van"},
            {
                "license_plate": "STU - 6789",
                "capacity_kg": 1500,
                "vehicle_type": "truck",
            },
            {
                "license_plate": "VWX - 0123",
                "capacity_kg": 1000,
                "vehicle_type": "truck",
            },
        ]

        for veh_data in vehicles_data:
            vehicle = Vehicle(
                license_plate=veh_data["license_plate"],
                capacity_kg=veh_data["capacity_kg"],
                vehicle_type=veh_data["vehicle_type"],
                is_active=True,
                fuel_efficiency_km_per_liter=random.uniform(8, 12),
            )
            self.db.add(vehicle)
            self.vehicles.append(vehicle)

        await self.db.commit()
        print(f"✅ Created {len(self.vehicles)} vehicles")

    async def create_customers(self, count: int = 50):
        """Create test customers"""
        print("🏠 Creating customers...")

        for i in range(count):
            city = random.choice(list(TAIWAN_DISTRICTS.keys()))
            district = random.choice(TAIWAN_DISTRICTS[city])
            street = random.choice(TAIWAN_STREETS)
            number = random.randint(1, 500)

            customer = Customer(
                customer_code=f"C{i + 1:05d}",
                name=f"測試客戶{i + 1}",
                customer_type=random.choice(CUSTOMER_TYPES),
                phone=f"09{random.randint(10000000, 99999999)}",
                delivery_address=f"{city}{district}{street}{number}號",
                delivery_latitude=25.0330 + random.uniform(-0.1, 0.1),
                delivery_longitude=121.5654 + random.uniform(-0.1, 0.1),
                contact_person=f"聯絡人{i + 1}",
                is_active=True,
                credit_limit=random.choice([30000, 50000, 100000, 200000]),
                payment_terms=random.choice([0, 30, 60]),
                discount_rate=random.choice([0, 0.05, 0.1]),
                notes=f"測試客戶備註 {i + 1}",
            )

            # Add some customers with email
            if random.random() > 0.7:
                customer.email = f"customer{i + 1}@test.com"

            self.db.add(customer)
            self.customers.append(customer)

        await self.db.commit()

        # Create customer inventories
        print("📦 Creating customer inventories...")
        for customer in self.customers[:30]:  # First 30 customers have inventory
            for product in self.products[:3]:  # Gas products only
                inventory = CustomerInventory(
                    customer_id=customer.id,
                    product_id=product.id,
                    quantity=random.randint(0, 5),
                    last_delivery_date=datetime.now()
                    - timedelta(days=random.randint(7, 30)),
                )
                self.db.add(inventory)

        await self.db.commit()
        print(f"✅ Created {len(self.customers)} customers with inventories")

    async def create_orders(self, count: int = 200):
        """Create test orders"""
        print("📋 Creating orders...")

        # Create historical orders (last 60 days)
        for i in range(count):
            customer = random.choice(self.customers)
            order_date = datetime.now() - timedelta(days=random.randint(0, 60))

            order = Order(
                order_number=f"ORD{order_date.strftime('%Y % m % d')}{i + 1:04d}",
                customer_id=customer.id,
                customer_name=customer.name,
                delivery_address=customer.delivery_address,
                delivery_latitude=customer.delivery_latitude,
                delivery_longitude=customer.delivery_longitude,
                phone=customer.phone,
                order_date=order_date,
                delivery_date=order_date + timedelta(days=random.randint(0, 3)),
                delivery_time_slot=random.choice(["morning", "afternoon", "evening"]),
                status=random.choice(ORDER_STATUSES),
                payment_method=random.choice(PAYMENT_METHODS),
                priority=random.choice(["normal", "high", "urgent"]),
                notes=f"測試訂單備註 {i + 1}" if random.random() > 0.7 else None,
                created_at=order_date,
                total_amount=0,  # Will be calculated
            )

            self.db.add(order)
            await self.db.flush()

            # Add order items
            num_items = random.randint(1, 3)
            total_amount = 0
            total_quantity = 0

            for j in range(num_items):
                product = random.choice(self.products[:4])  # Gas products only
                quantity = random.randint(1, 5)
                unit_price = product.price
                subtotal = quantity * unit_price

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )

                self.db.add(order_item)
                total_amount += subtotal
                total_quantity += quantity

            order.total_amount = total_amount
            order.total_quantity = total_quantity
            self.orders.append(order)

        await self.db.commit()
        print(f"✅ Created {len(self.orders)} orders")

    async def create_routes(self):
        """Create test routes with deliveries"""
        print("🗺️ Creating routes...")

        # Group orders by date and status
        pending_orders = [
            o for o in self.orders if o.status in ["pending", "confirmed"]
        ]

        # Create routes for the next 7 days
        for day_offset in range(7):
            route_date = date.today() + timedelta(days=day_offset)

            # Create 2 - 3 routes per day
            num_routes = random.randint(2, 3)

            for route_num in range(num_routes):
                driver = random.choice(
                    [u for u in self.users if u.role == UserRole.DRIVER]
                )
                vehicle = random.choice(self.vehicles)

                route = Route(
                    route_number=f"R{route_date.strftime('%Y % m % d')}{route_num + 1:02d}",
                    route_date=route_date,
                    driver_id=driver.id,
                    vehicle_id=vehicle.id,
                    status=random.choice(ROUTE_STATUSES),
                    start_location="台北市中正區重慶南路一段122號",  # Lucky Gas HQ
                    end_location="台北市中正區重慶南路一段122號",
                    total_distance_km=random.uniform(20, 100),
                    total_duration_minutes=random.randint(120, 480),
                    optimization_score=random.uniform(0.7, 0.95),
                    notes=f"測試路線 {route_num + 1}",
                )

                self.db.add(route)
                await self.db.flush()

                # Assign 5 - 15 orders to each route
                route_orders = random.sample(
                    [o for o in pending_orders if o.delivery_date.date() == route_date],
                    min(
                        random.randint(5, 15),
                        len(
                            [
                                o
                                for o in pending_orders
                                if o.delivery_date.date() == route_date
                            ]
                        ),
                    ),
                )

                for seq, order in enumerate(route_orders):
                    route_delivery = RouteDelivery(
                        route_id=route.id,
                        order_id=order.id,
                        sequence=seq + 1,
                        estimated_arrival_time=datetime.combine(
                            route_date, datetime.min.time()
                        )
                        + timedelta(hours=8 + seq * 0.5),
                        distance_from_previous_km=random.uniform(1, 10),
                        duration_from_previous_minutes=random.randint(5, 30),
                        status="pending",
                    )
                    self.db.add(route_delivery)

                self.routes.append(route)

        await self.db.commit()
        print(f"✅ Created {len(self.routes)} routes")

    async def create_delivery_history(self):
        """Create delivery history for completed orders"""
        print("📜 Creating delivery history...")

        completed_orders = [o for o in self.orders if o.status == "delivered"]

        for order in completed_orders[:50]:  # First 50 completed orders
            delivery = DeliveryHistory(
                order_id=order.id,
                customer_id=order.customer_id,
                delivery_date=order.delivery_date,
                delivered_by=random.choice(
                    [u.id for u in self.users if u.role == UserRole.DRIVER]
                ),
                signature_image=None,
                delivery_photo=None,
                notes=f"已成功送達 - {order.customer_name}",
                delivery_latitude=order.delivery_latitude
                + random.uniform(-0.001, 0.001),
                delivery_longitude=order.delivery_longitude
                + random.uniform(-0.001, 0.001),
                delivery_time=order.delivery_date
                + timedelta(hours=random.randint(8, 18)),
            )

            self.db.add(delivery)
            await self.db.flush()

            # Add delivery items
            result = await self.db.execute(
                select(OrderItem).filter(OrderItem.order_id == order.id)
            )
            order_items = result.scalars().all()

            for item in order_items:
                delivery_item = DeliveryHistoryItem(
                    delivery_history_id=delivery.id,
                    product_id=item.product_id,
                    quantity_delivered=item.quantity,
                    quantity_empty_returned=(
                        random.randint(0, item.quantity) if random.random() > 0.5 else 0
                    ),
                )
                self.db.add(delivery_item)

        await self.db.commit()
        print("✅ Created delivery history")

    async def create_notifications(self):
        """Create test notifications"""
        print("🔔 Creating notifications...")

        notification_templates = [
            ("order_created", "新訂單通知", "您有一筆新訂單 {order_number}"),
            ("route_assigned", "路線指派通知", "您已被指派到路線 {route_number}"),
            ("delivery_completed", "送貨完成通知", "訂單 {order_number} 已送達"),
            ("payment_received", "付款通知", "已收到付款 NT${amount}"),
            ("low_stock", "庫存警告", "{product_name} 庫存不足"),
        ]

        for i in range(30):
            template = random.choice(notification_templates)
            user = random.choice(self.users)

            notification = Notification(
                user_id=user.id,
                type=template[0],
                title=template[1],
                message=template[2].format(
                    order_number=f"ORD{random.randint(10000, 99999)}",
                    route_number=f"R{random.randint(1000, 9999)}",
                    amount=random.randint(1000, 10000),
                    product_name="20公斤桶裝瓦斯",
                ),
                is_read=random.choice([True, False]),
                created_at=datetime.now() - timedelta(days=random.randint(0, 7)),
            )

            self.db.add(notification)

        await self.db.commit()
        print("✅ Created notifications")

    async def create_order_templates(self):
        """Create order templates for regular customers"""
        print("📑 Creating order templates...")

        # Create templates for first 20 customers
        for customer in self.customers[:20]:
            template = OrderTemplate(
                customer_id=customer.id,
                template_name=f"{customer.name} - 標準訂單",
                is_active=True,
                frequency=random.choice(["weekly", "biweekly", "monthly"]),
                notes=f"標準配送模板 - {customer.name}",
            )

            self.db.add(template)
            await self.db.flush()

            # Add template items
            for product in random.sample(self.products[:4], random.randint(1, 3)):
                template.items.append(
                    {"product_id": product.id, "quantity": random.randint(1, 5)}
                )

        await self.db.commit()
        print("✅ Created order templates")


async def main():
    """Main function to initialize test data"""
    print("🚀 Starting Lucky Gas Test Data Initialization")
    print("=" * 50)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize data
    async for db in get_db():
        generator = TestDataGenerator(db)

        try:
            # Clean existing data
            await generator.clean_database()

            # Create test data in order
            await generator.create_users()
            await generator.create_gas_products()
            await generator.create_vehicles()
            await generator.create_customers(count=50)
            await generator.create_orders(count=200)
            await generator.create_routes()
            await generator.create_delivery_history()
            await generator.create_notifications()
            await generator.create_order_templates()

            print("\n" + "=" * 50)
            print("✅ Test data initialization completed successfully!")
            print("\n📊 Summary:")
            print(f"  - Users: {len(generator.users)}")
            print(f"  - Customers: {len(generator.customers)}")
            print(f"  - Products: {len(generator.products)}")
            print(f"  - Orders: {len(generator.orders)}")
            print(f"  - Routes: {len(generator.routes)}")
            print(f"  - Vehicles: {len(generator.vehicles)}")

            print("\n🔑 Test Credentials:")
            print("  Admin: admin@test.luckygas.tw / TestAdmin123!")
            print("  Manager: manager1@test.luckygas.tw / Manager123!")
            print("  Staff: staff1@test.luckygas.tw / Staff123!")
            print("  Driver: driver1@test.luckygas.tw / Driver123!")

        except Exception as e:
            print(f"\n❌ Error during initialization: {str(e)}")
            await db.rollback()
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())
