#!/usr/bin/env python3
"""
Initialize Lucky Gas database with tables and seed data
Designed for PostgreSQL but works with SQLite too
"""

import sys
import os
import logging

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after path is set
from app.core.database import engine, SessionLocal, Base
from app.models import User, Customer, Order, Driver, UserRole
from app.api.v1.auth import get_password_hash
from app.core.config import settings
from datetime import datetime
from sqlalchemy import text


def create_tables():
    """Create all database tables"""
    logger.info("🔨 Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        return False


def create_admin_user(db: SessionLocal):
    """Create the admin user if it doesn't exist"""
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.email == settings.FIRST_SUPERUSER).first()
        
        if not admin:
            admin = User(
                email=settings.FIRST_SUPERUSER,
                username="admin",
                full_name="System Administrator",
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(admin)
            db.commit()
            logger.info(f"✅ Admin user created: {settings.FIRST_SUPERUSER}")
        else:
            logger.info(f"ℹ️ Admin user already exists: {settings.FIRST_SUPERUSER}")
        
        return admin
    except Exception as e:
        logger.error(f"❌ Failed to create admin user: {e}")
        db.rollback()
        raise


def create_sample_products(db: SessionLocal):
    """Create sample products if none exist"""
    # Product model not available in simplified version
    return
    try:
        if False:  # db.query(Product).count() == 0:
            from app.models import ProductType
            products = [
                Product(
                    code="GAS-20KG",
                    name="20公斤瓦斯桶",  # 20kg Gas Cylinder
                    product_type=ProductType.GAS_20KG,
                    unit_price=800.0,
                    current_stock=50,
                    min_stock_level=10,
                    is_active=True
                ),
                Product(
                    code="GAS-50KG",
                    name="50公斤瓦斯桶",  # 50kg Gas Cylinder
                    product_type=ProductType.GAS_50KG,
                    unit_price=2000.0,
                    current_stock=30,
                    min_stock_level=5,
                    is_active=True
                ),
                Product(
                    code="GAS-16KG",
                    name="16公斤瓦斯桶",  # 16kg Gas Cylinder
                    product_type=ProductType.GAS_16KG,
                    unit_price=650.0,
                    current_stock=40,
                    min_stock_level=8,
                    is_active=True
                ),
                Product(
                    code="GAS-10KG",
                    name="10公斤瓦斯桶",  # 10kg Gas Cylinder
                    product_type=ProductType.GAS_10KG,
                    unit_price=450.0,
                    current_stock=20,
                    min_stock_level=5,
                    is_active=True
                ),
                Product(
                    code="ACC-REGULATOR",
                    name="調壓器",  # Regulator
                    product_type=ProductType.ACCESSORY,
                    unit_price=250.0,
                    current_stock=25,
                    min_stock_level=5,
                    is_active=True
                ),
            ]
            
            for product in products:
                db.add(product)
            
            db.commit()
            logger.info(f"✅ Created {len(products)} sample products")
        else:
            logger.info(f"ℹ️ Products already exist ({db.query(Product).count()} found)")
    except Exception as e:
        logger.error(f"❌ Failed to create sample products: {e}")
        db.rollback()
        raise


def create_sample_drivers(db: SessionLocal):
    """Create sample drivers if none exist"""
    try:
        if db.query(Driver).count() == 0:
            # Create driver users first
            driver_users = [
                User(
                    email="driver1@luckygas.com",
                    username="driver1",
                    full_name="陳大明",  # Chen Da-Ming
                    hashed_password=get_password_hash("driver123"),
                    role=UserRole.DRIVER,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                User(
                    email="driver2@luckygas.com",
                    username="driver2",
                    full_name="李小華",  # Li Xiao-Hua
                    hashed_password=get_password_hash("driver123"),
                    role=UserRole.DRIVER,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
            ]
            
            for user in driver_users:
                db.add(user)
            db.flush()  # Flush to get user IDs
            
            # Create drivers linked to users
            drivers = [
                Driver(
                    user_id=driver_users[0].id,
                    driver_code="DRV001",
                    license_number="TW-DRV-001",
                    phone="0912-345-678",
                    max_daily_deliveries=30,
                    is_active=True,
                    is_available=True
                ),
                Driver(
                    user_id=driver_users[1].id,
                    driver_code="DRV002",
                    license_number="TW-DRV-002",
                    phone="0923-456-789",
                    max_daily_deliveries=25,
                    is_active=True,
                    is_available=True
                ),
            ]
            
            for driver in drivers:
                db.add(driver)
            db.flush()  # Flush to get driver IDs
            
            # Vehicle model not available in simplified version
            """
            # Create vehicles assigned to drivers
            vehicles = [
                Vehicle(
                    driver_id=drivers[0].id,
                    license_plate="ABC-123",
                    vehicle_type="truck",
                    capacity_kg=1000.0,  # Can carry 1000kg
                    is_active=True
                ),
                Vehicle(
                    driver_id=drivers[1].id,
                    license_plate="XYZ-789",
                    vehicle_type="van",
                    capacity_kg=500.0,  # Can carry 500kg
                    is_active=True
                ),
            ]
            
            """
            for vehicle in vehicles:
                db.add(vehicle)
            
            db.commit()
            logger.info(f"✅ Created {len(driver_users)} driver users, {len(drivers)} drivers, and {len(vehicles)} vehicles")
        else:
            logger.info(f"ℹ️ Drivers already exist ({db.query(Driver).count()} found)")
    except Exception as e:
        logger.error(f"❌ Failed to create sample drivers: {e}")
        db.rollback()
        raise


def create_sample_customers(db: SessionLocal):
    """Create a few sample customers if none exist"""
    try:
        if db.query(Customer).count() == 0:
            from app.models import CustomerType
            customers = [
                Customer(
                    code="C001",
                    name="王記餐廳",  # Wang's Restaurant
                    phone="02-2345-6789",
                    email="wang.restaurant@example.com",
                    address="台北市信義區信義路五段7號",
                    area="信義區",
                    customer_type=CustomerType.RESTAURANT,
                    pricing_tier="commercial",
                    credit_limit=50000.0,
                    current_balance=0.0,
                    preferred_delivery_time="09:00-12:00",
                    notes="大型餐廳，每週需求穩定"
                ),
                Customer(
                    code="C002",
                    name="張太太",  # Mrs. Zhang
                    phone="0912-111-222",
                    email="zhang@example.com",
                    address="台北市大安區和平東路三段123號",
                    area="大安區",
                    customer_type=CustomerType.RESIDENTIAL,
                    pricing_tier="standard",
                    credit_limit=5000.0,
                    current_balance=0.0,
                    preferred_delivery_time="14:00-17:00",
                    notes="住宅用戶，偏好下午送貨"
                ),
                Customer(
                    code="C003",
                    name="幸福小吃店",  # Happy Snack Shop
                    phone="02-8765-4321",
                    email="happy.shop@example.com",
                    address="台北市中山區民生東路二段88號",
                    area="中山區",
                    customer_type=CustomerType.RESTAURANT,
                    pricing_tier="commercial",
                    credit_limit=30000.0,
                    current_balance=0.0,
                    preferred_delivery_time="08:00-10:00",
                    notes="早餐店，需要早上送貨"
                ),
            ]
            
            for customer in customers:
                db.add(customer)
            
            db.commit()
            logger.info(f"✅ Created {len(customers)} sample customers")
        else:
            logger.info(f"ℹ️ Customers already exist ({db.query(Customer).count()} found)")
    except Exception as e:
        logger.error(f"❌ Failed to create sample customers: {e}")
        db.rollback()
        raise


def init_db():
    """Initialize database with all tables and seed data"""
    logger.info("🚀 Starting database initialization...")
    logger.info(f"📍 Database URL: {os.getenv('DATABASE_URL', 'Not set - using default')}")
    
    # Create tables
    if not create_tables():
        logger.error("Failed to create tables. Exiting.")
        return False
    
    # Create seed data
    db = SessionLocal()
    try:
        # Create admin user
        create_admin_user(db)
        
        # Create sample data
        create_sample_products(db)
        create_sample_drivers(db)
        create_sample_customers(db)
        
        # Commit any pending changes
        db.commit()
        
        logger.info("✅ Database initialization complete!")
        logger.info("")
        logger.info("📊 Database Summary:")
        logger.info(f"  • Users: {db.query(User).count()}")
        logger.info(f"  • Customers: {db.query(Customer).count()}")
        # logger.info(f"  • Products: {db.query(Product).count()}")
        logger.info(f"  • Drivers: {db.query(Driver).count()}")
        # logger.info(f"  • Vehicles: {db.query(Vehicle).count()}")
        logger.info("")
        logger.info("🔐 Admin Login:")
        logger.info(f"  Email: {settings.FIRST_SUPERUSER}")
        logger.info(f"  Password: {settings.FIRST_SUPERUSER_PASSWORD}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # Load environment variables from .env.local if it exists
    from dotenv import load_dotenv
    env_file = os.path.join(os.path.dirname(__file__), '.env.local')
    if os.path.exists(env_file):
        logger.info(f"📄 Loading environment from {env_file}")
        load_dotenv(env_file, override=True)
    
    # Run initialization
    success = init_db()
    sys.exit(0 if success else 1)