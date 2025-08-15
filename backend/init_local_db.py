#!/usr/bin/env python3
"""
Initialize Lucky Gas local database with proper model imports.
"""
import os
import sys
import asyncio
import logging

# Set up path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Use local environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./local_luckygas.db"
os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "local-dev-secret-key-change-in-production"
os.environ["FIRST_SUPERUSER"] = "admin@luckygas.com"
os.environ["FIRST_SUPERUSER_PASSWORD"] = "admin-password-2025"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():
    """Initialize database with all models properly imported."""
    try:
        # Import database_simple first
        from app.core import database_simple
        
        # Monkey patch the database module to use our simple version
        import app.core.database as old_db
        old_db.Base = database_simple.Base
        old_db.get_async_session = database_simple.get_async_session
        
        # Now import all models in the correct order to avoid circular dependencies
        logger.info("Importing models...")
        
        # Core models first
        from app.models.user import User, UserRole
        from app.models.driver import Driver
        
        # Import all models to ensure relationships are registered
        # This is a bit brute force but ensures all models are loaded
        try:
            from app.models.order_template import OrderTemplate
        except Exception as e:
            logger.warning(f"Could not import OrderTemplate: {e}")
        
        from app.models.customer import Customer
        from app.models.order import Order, OrderStatus
        from app.models.delivery import Delivery
        from app.models.route import Route
        
        # Try importing other models but don't fail if they don't exist
        try:
            from app.models.notification import Notification
        except:
            pass
        try:
            from app.models.feature_flag import FeatureFlag
        except:
            pass
        
        logger.info("✅ Models imported successfully")
        
        # Initialize database
        await database_simple.initialize_database()
        
        # Create tables
        await database_simple.create_db_and_tables()
        
        # Create admin user
        from app.core.security import get_password_hash
        from sqlalchemy import select
        
        async for db in database_simple.get_async_session():
            # Check if admin exists
            result = await db.execute(
                select(User).where(User.username == "admin@luckygas.com")
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                admin = User(
                    email="admin@luckygas.com",
                    username="admin@luckygas.com",
                    full_name="System Administrator",
                    hashed_password=get_password_hash("admin-password-2025"),
                    is_active=True,
                    role=UserRole.SUPER_ADMIN
                )
                db.add(admin)
                await db.commit()
                logger.info("✅ Admin user created")
            else:
                logger.info("✅ Admin user already exists")
            
            # Create sample driver
            result = await db.execute(
                select(Driver).where(Driver.code == "D001")
            )
            driver = result.scalar_one_or_none()
            
            if not driver:
                driver = Driver(
                    code="D001",
                    name="張師傅",
                    phone="0912345678",
                    is_active=True,
                    max_daily_orders=30,
                    vehicle_type="truck",
                    license_plate="ABC-1234"
                )
                db.add(driver)
                await db.commit()
                logger.info("✅ Sample driver created")
            
            # Create sample customer
            result = await db.execute(
                select(Customer).where(Customer.customer_code == "C001")
            )
            customer = result.scalar_one_or_none()
            
            if not customer:
                customer = Customer(
                    customer_code="C001",
                    short_name="測試餐廳",
                    invoice_title="測試餐廳有限公司",
                    address="台北市信義區信義路五段7號",
                    cylinders_20kg=2,
                    cylinders_50kg=1,
                    area="信義區",
                    customer_type="restaurant",
                    is_subscription=True
                )
                db.add(customer)
                await db.commit()
                logger.info("✅ Sample customer created")
            
            break
        
        logger.info("✅ Database initialized successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api():
    """Test the API with the initialized database."""
    import httpx
    
    logger.info("\n" + "="*60)
    logger.info("Testing API endpoints...")
    logger.info("="*60)
    
    # Start the server
    import uvicorn
    from app.main import app
    import threading
    import time
    
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(2)
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        logger.info("\n1. Testing health endpoint...")
        response = await client.get("http://127.0.0.1:8001/health")
        logger.info(f"   Status: {response.status_code}")
        logger.info(f"   Response: {response.json()}")
        
        # Test login
        logger.info("\n2. Testing login...")
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
            logger.info(f"   Token: {access_token[:50]}...")
            
            # Test authenticated endpoints
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Get current user
            logger.info("\n3. Testing current user endpoint...")
            response = await client.get(
                "http://127.0.0.1:8001/api/v1/auth/me",
                headers=headers
            )
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"   ✅ Current user: {user_data.get('username')}")
            else:
                logger.error(f"   ❌ Failed: {response.status_code}")
            
            # Get customers
            logger.info("\n4. Testing customers endpoint...")
            response = await client.get(
                "http://127.0.0.1:8001/api/v1/customers",
                headers=headers
            )
            if response.status_code == 200:
                customers = response.json()
                logger.info(f"   ✅ Found {len(customers)} customers")
            else:
                logger.error(f"   ❌ Failed: {response.status_code}")
            
            # Get drivers
            logger.info("\n5. Testing drivers endpoint...")
            response = await client.get(
                "http://127.0.0.1:8001/api/v1/drivers",
                headers=headers
            )
            if response.status_code == 200:
                drivers = response.json()
                logger.info(f"   ✅ Found {len(drivers)} drivers")
            else:
                logger.error(f"   ❌ Failed: {response.status_code}")
                
        else:
            logger.error(f"   ❌ Login failed: {response.status_code} - {response.text}")
    
    logger.info("\n" + "="*60)
    logger.info("API testing completed!")
    logger.info("="*60)


async def main():
    """Run all initialization and tests."""
    logger.info("="*60)
    logger.info("Lucky Gas Local Development Setup")
    logger.info("="*60)
    
    # Initialize database
    if await init_db():
        # Test API
        await test_api()
        
        logger.info("\n" + "🎉"*20)
        logger.info("✅ Local development environment is ready!")
        logger.info("🎉"*20)
        logger.info("\nYou can now run the backend with:")
        logger.info("  uv run uvicorn app.main:app --reload")
        logger.info("\nOr use the full backend with:")
        logger.info("  uv run uvicorn app.main:app --reload")
    else:
        logger.error("\n❌ Setup failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())