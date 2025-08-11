#!/usr/bin/env python3
"""
Initial data import script for LuckyGas system.
Imports customers and creates sample data for testing.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import asyncpg

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_initial_admin():
    """Create initial admin user if it doesn't exist."""
    conn = None
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql'))
        
        # Check if admin user exists
        existing_admin = await conn.fetchrow("SELECT id FROM users WHERE email = $1", settings.FIRST_SUPERUSER)
        
        if existing_admin:
            print(f"✓ Admin user already exists: {settings.FIRST_SUPERUSER}")
            return existing_admin['id']
            
        # Create admin user
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
        
        admin_id = await conn.fetchval("""
            INSERT INTO users (email, hashed_password, full_name, role, is_active, is_verified, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """, settings.FIRST_SUPERUSER, hashed_password, "系統管理員", "super_admin", True, True, datetime.utcnow(), datetime.utcnow())
        
        print(f"✓ Created admin user: {settings.FIRST_SUPERUSER} (ID: {admin_id})")
        return admin_id
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return None
    finally:
        if conn:
            await conn.close()


async def import_sample_customers():
    """Import sample customers."""
    conn = None
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql'))
        
        # Check if customers already exist
        existing_count = await conn.fetchval("SELECT COUNT(*) FROM customers")
        if existing_count > 0:
            print(f"✓ Database already has {existing_count} customers")
            return
        
        # Sample customer data
        sample_customers = [
            {
                'name': '王大明', 
                'phone': '0912345678', 
                'email': 'wang@example.com',
                'address': '台北市大安區信義路四段123號',
                'customer_code': 'C001'
            },
            {
                'name': '李小華', 
                'phone': '0987654321', 
                'email': 'li@example.com',
                'address': '台北市中山區南京東路二段456號',
                'customer_code': 'C002'
            },
            {
                'name': '陳美玲', 
                'phone': '0923456789', 
                'email': 'chen@example.com',
                'address': '新北市板橋區文化路三段789號',
                'customer_code': 'C003'
            },
            {
                'name': '張志明', 
                'phone': '0934567890', 
                'email': 'zhang@example.com',
                'address': '桃園市中壢區中正路一段321號',
                'customer_code': 'C004'
            },
            {
                'name': '劉雅雯', 
                'phone': '0945678901', 
                'email': 'liu@example.com',
                'address': '台中市西區台灣大道二段654號',
                'customer_code': 'C005'
            }
        ]
        
        # Insert sample customers
        inserted_count = 0
        for customer in sample_customers:
            try:
                customer_id = await conn.fetchval("""
                    INSERT INTO customers (name, phone, email, address, customer_code, 
                                        is_active, latitude, longitude, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                """, customer['name'], customer['phone'], customer['email'], 
                    customer['address'], customer['customer_code'], True,
                    25.0330, 121.5654,  # Default coordinates (Taipei)
                    datetime.utcnow(), datetime.utcnow())
                inserted_count += 1
                print(f"✓ Created customer: {customer['name']} (ID: {customer_id})")
            except Exception as e:
                print(f"❌ Failed to create customer {customer['name']}: {e}")
        
        print(f"✓ Imported {inserted_count} sample customers")
        
    except Exception as e:
        print(f"❌ Error importing customers: {e}")
    finally:
        if conn:
            await conn.close()


async def create_gas_products():
    """Create standard gas products if they don't exist."""
    conn = None
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql'))
        
        # Check if products already exist
        existing_count = await conn.fetchval("SELECT COUNT(*) FROM gas_products")
        if existing_count > 0:
            print(f"✓ Database already has {existing_count} gas products")
            return
        
        # Standard Taiwan gas cylinder products
        products = [
            {'name_zh': '50公斤液化瓦斯', 'size_kg': 50, 'unit_price': 1200.0, 'sku': 'GAS50'},
            {'name_zh': '20公斤液化瓦斯', 'size_kg': 20, 'unit_price': 600.0, 'sku': 'GAS20'},
            {'name_zh': '16公斤液化瓦斯', 'size_kg': 16, 'unit_price': 500.0, 'sku': 'GAS16'},
            {'name_zh': '10公斤液化瓦斯', 'size_kg': 10, 'unit_price': 350.0, 'sku': 'GAS10'},
            {'name_zh': '4公斤液化瓦斯', 'size_kg': 4, 'unit_price': 200.0, 'sku': 'GAS04'},
        ]
        
        inserted_count = 0
        for product in products:
            try:
                product_id = await conn.fetchval("""
                    INSERT INTO gas_products (name_zh, size_kg, unit_price, sku, 
                                            delivery_method, attribute, is_active, is_available, track_inventory)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                """, product['name_zh'], product['size_kg'], product['unit_price'], 
                    product['sku'], 'CYLINDER', 'REGULAR', True, True, True)
                inserted_count += 1
                print(f"✓ Created product: {product['name_zh']} (ID: {product_id})")
            except Exception as e:
                print(f"❌ Failed to create product {product['name_zh']}: {e}")
        
        print(f"✓ Imported {inserted_count} gas products")
        
    except Exception as e:
        print(f"❌ Error importing products: {e}")
    finally:
        if conn:
            await conn.close()


async def create_sample_orders():
    """Create sample orders for testing."""
    conn = None
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql'))
        
        # Check if orders already exist
        existing_count = await conn.fetchval("SELECT COUNT(*) FROM orders")
        if existing_count > 0:
            print(f"✓ Database already has {existing_count} orders")
            return
        
        # Get customer IDs and product IDs
        customers = await conn.fetch("SELECT id FROM customers LIMIT 5")
        products = await conn.fetch("SELECT id, unit_price FROM gas_products LIMIT 3")
        
        if not customers or not products:
            print("❌ Need customers and products before creating orders")
            return
        
        # Create sample orders
        inserted_count = 0
        for i, customer in enumerate(customers):
            product = products[i % len(products)]
            
            try:
                # Create order
                order_id = await conn.fetchval("""
                    INSERT INTO orders (customer_id, order_date, delivery_date, status, 
                                      total_amount, notes, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id
                """, customer['id'], datetime.utcnow().date(),
                    datetime.utcnow().date() + timedelta(days=1),
                    'pending', float(product['unit_price']), 
                    f'測試訂單 #{i+1}', datetime.utcnow(), datetime.utcnow())
                
                # Create order item
                await conn.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, 
                                           total_price, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, order_id, product['id'], 1, float(product['unit_price']), 
                    float(product['unit_price']), datetime.utcnow(), datetime.utcnow())
                
                inserted_count += 1
                print(f"✓ Created order #{order_id} for customer {customer['id']}")
                
            except Exception as e:
                print(f"❌ Failed to create order for customer {customer['id']}: {e}")
        
        print(f"✓ Created {inserted_count} sample orders")
        
    except Exception as e:
        print(f"❌ Error creating sample orders: {e}")
    finally:
        if conn:
            await conn.close()


async def main():
    """Main import process."""
    print("🚀 Starting initial data import...")
    print(f"Database URL: {settings.POSTGRES_SERVER}")
    print(f"Database: {settings.POSTGRES_DB}")
    
    # Test database connection
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql'))
        await conn.close()
        print("✓ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Run import steps
    try:
        await create_initial_admin()
        await create_gas_products()
        await import_sample_customers()
        await create_sample_orders()
        
        print("✅ Initial data import completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)