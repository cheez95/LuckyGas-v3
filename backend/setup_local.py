#!/usr/bin/env python3
"""
Setup Lucky Gas local development environment with simplified models.
"""
import os
import sys
import asyncio
import logging

# Set up path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Use local environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./luckygas_local.db"
os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "local-dev-secret-key-32-chars-long"
os.environ["FIRST_SUPERUSER"] = "admin@luckygas.com"
os.environ["FIRST_SUPERUSER_PASSWORD"] = "admin-password-2025"

# Disable cloud features
os.environ["DISABLE_CLOUD_SQL"] = "true"
os.environ["DISABLE_GCP"] = "true"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_database():
    """Setup database with simplified models."""
    try:
        # Import database setup
        from app.core import database_simple
        
        # Import simplified models
        from app import models_simple
        
        # Initialize database
        logger.info("Initializing SQLite database...")
        await database_simple.initialize_database()
        
        # Create all tables from simplified models
        logger.info("Creating database tables...")
        async with database_simple.engine.begin() as conn:
            await conn.run_sync(models_simple.Base.metadata.create_all)
        
        logger.info("✅ Database setup complete!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def create_sample_data():
    """Create sample data for testing."""
    try:
        from app.core.database_async import get_async_session
        from app.models import User, UserRole, Customer, CustomerType, Driver, Order, OrderStatus, Route
        from app.core.security import get_password_hash
        from sqlalchemy import select
        from datetime import datetime, timedelta
        
        logger.info("Creating sample data...")
        
        async for db in get_async_session():
            # Create admin user
            result = await db.execute(
                select(User).where(User.username == "admin@luckygas.com")
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                admin = User(
                    email="admin@luckygas.com",
                    username="admin@luckygas.com",
                    full_name="系統管理員",
                    hashed_password=get_password_hash("admin-password-2025"),
                    is_active=True,
                    role=UserRole.SUPER_ADMIN
                )
                db.add(admin)
                logger.info("  ✅ Admin user created")
            
            # Create sample drivers
            drivers_data = [
                {"code": "D001", "name": "張師傅", "phone": "0912345678", "vehicle_type": "truck", "license_plate": "ABC-1234"},
                {"code": "D002", "name": "李師傅", "phone": "0923456789", "vehicle_type": "truck", "license_plate": "XYZ-5678"},
                {"code": "D003", "name": "王師傅", "phone": "0934567890", "vehicle_type": "motorcycle", "license_plate": "123-ABC"},
            ]
            
            for driver_data in drivers_data:
                result = await db.execute(
                    select(Driver).where(Driver.code == driver_data["code"])
                )
                if not result.scalar_one_or_none():
                    driver = Driver(**driver_data, is_active=True, max_daily_orders=30)
                    db.add(driver)
            logger.info(f"  ✅ Created {len(drivers_data)} drivers")
            
            # Create sample customers
            customers_data = [
                {
                    "customer_code": "C001",
                    "short_name": "福來餐廳",
                    "invoice_title": "福來餐廳有限公司",
                    "address": "台北市信義區信義路五段7號",
                    "phone": "02-27581234",
                    "cylinders_20kg": 2,
                    "cylinders_50kg": 1,
                    "area": "信義區",
                    "customer_type": CustomerType.RESTAURANT,
                    "is_subscription": True
                },
                {
                    "customer_code": "C002",
                    "short_name": "張家",
                    "invoice_title": "張先生",
                    "address": "台北市大安區復興南路二段123號5樓",
                    "phone": "0911222333",
                    "cylinders_20kg": 1,
                    "area": "大安區",
                    "customer_type": CustomerType.RESIDENTIAL,
                    "is_subscription": False
                },
                {
                    "customer_code": "C003",
                    "short_name": "明德工廠",
                    "invoice_title": "明德工業股份有限公司",
                    "address": "新北市三重區重新路五段609號",
                    "phone": "02-29991234",
                    "cylinders_50kg": 3,
                    "area": "三重區",
                    "customer_type": CustomerType.INDUSTRIAL,
                    "is_subscription": True
                }
            ]
            
            for customer_data in customers_data:
                result = await db.execute(
                    select(Customer).where(Customer.customer_code == customer_data["customer_code"])
                )
                if not result.scalar_one_or_none():
                    customer = Customer(**customer_data, is_active=True)
                    db.add(customer)
            logger.info(f"  ✅ Created {len(customers_data)} customers")
            
            # Create sample orders
            today = datetime.now()
            orders_data = [
                {
                    "order_number": f"ORD-{today.strftime('%Y%m%d')}-001",
                    "customer_id": 1,
                    "status": OrderStatus.PENDING,
                    "delivery_date": today + timedelta(days=1),
                    "qty_20kg": 2,
                    "qty_50kg": 1,
                    "total_amount": 3500.0,
                    "notes": "請於早上9點前送達"
                },
                {
                    "order_number": f"ORD-{today.strftime('%Y%m%d')}-002",
                    "customer_id": 2,
                    "status": OrderStatus.CONFIRMED,
                    "delivery_date": today + timedelta(days=1),
                    "qty_20kg": 1,
                    "total_amount": 1200.0,
                    "notes": "下午送達即可"
                },
                {
                    "order_number": f"ORD-{today.strftime('%Y%m%d')}-003",
                    "customer_id": 3,
                    "status": OrderStatus.PENDING,
                    "delivery_date": today + timedelta(days=2),
                    "qty_50kg": 3,
                    "total_amount": 4500.0,
                    "notes": "工廠後門卸貨"
                }
            ]
            
            for order_data in orders_data:
                result = await db.execute(
                    select(Order).where(Order.order_number == order_data["order_number"])
                )
                if not result.scalar_one_or_none():
                    order = Order(**order_data)
                    db.add(order)
            logger.info(f"  ✅ Created {len(orders_data)} orders")
            
            # Create sample route
            result = await db.execute(
                select(Route).where(Route.route_date == today.date())
            )
            if not result.scalar_one_or_none():
                route = Route(
                    route_code=f"RT-{today.strftime('%Y%m%d')}-001",
                    route_date=today,
                    driver_id=1,
                    total_stops=3,
                    completed_stops=0,
                    total_distance=25.5,
                    is_optimized=False,
                    is_completed=False
                )
                db.add(route)
                logger.info("  ✅ Created sample route")
            
            # Commit all changes
            await db.commit()
            logger.info("✅ Sample data created successfully!")
            break
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create sample data: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api():
    """Test the API endpoints."""
    import httpx
    from app.main import app
    import uvicorn
    import threading
    import time
    
    logger.info("\n" + "="*60)
    logger.info("Testing API endpoints...")
    logger.info("="*60)
    
    # Start server in background
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(2)
    
    async with httpx.AsyncClient() as client:
        # 1. Test health
        logger.info("\n1. Health check...")
        response = await client.get("http://127.0.0.1:8001/health")
        logger.info(f"   Status: {response.status_code}")
        if response.status_code == 200:
            logger.info(f"   ✅ {response.json()}")
        
        # 2. Test login
        logger.info("\n2. Login test...")
        response = await client.post(
            "http://127.0.0.1:8001/api/v1/auth/login",
            data={
                "username": "admin@luckygas.com",
                "password": "admin-password-2025"
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            logger.info(f"   ✅ Login successful!")
            logger.info(f"   Token: {access_token[:30]}...")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 3. Test authenticated endpoints
            endpoints = [
                ("/api/v1/auth/me", "Current user"),
                ("/api/v1/customers", "Customers"),
                ("/api/v1/drivers", "Drivers"),
                ("/api/v1/orders", "Orders"),
            ]
            
            for endpoint, name in endpoints:
                logger.info(f"\n3. Testing {name}...")
                response = await client.get(
                    f"http://127.0.0.1:8001{endpoint}",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        logger.info(f"   ✅ {name}: Found {len(data)} items")
                    else:
                        logger.info(f"   ✅ {name}: {data.get('username', data.get('email', 'OK'))}")
                else:
                    logger.error(f"   ❌ {name}: {response.status_code}")
        else:
            logger.error(f"   ❌ Login failed: {response.status_code}")
    
    logger.info("\n" + "="*60)
    logger.info("API testing completed!")
    logger.info("="*60)


async def main():
    """Main setup function."""
    logger.info("\n" + "🚀"*20)
    logger.info("Lucky Gas Local Development Setup")
    logger.info("🚀"*20 + "\n")
    
    # Setup database
    if not await setup_database():
        logger.error("Failed to setup database. Exiting.")
        return
    
    # Create sample data
    if not await create_sample_data():
        logger.error("Failed to create sample data. Exiting.")
        return
    
    # Test API
    await test_api()
    
    logger.info("\n" + "🎉"*20)
    logger.info("✅ Local development environment is ready!")
    logger.info("🎉"*20)
    
    logger.info("\nTo start the backend server:")
    logger.info("  uv run uvicorn app.main:app --reload --port 8000")
    
    logger.info("\nTo access the API documentation:")
    logger.info("  http://localhost:8000/docs")
    
    logger.info("\nDefault credentials:")
    logger.info("  Username: admin@luckygas.com")
    logger.info("  Password: admin-password-2025")


if __name__ == "__main__":
    asyncio.run(main())