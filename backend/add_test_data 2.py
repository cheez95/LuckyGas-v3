#!/usr/bin/env python3
"""
Add test data to database for functionality testing
"""
import asyncio
import asyncpg
from datetime import datetime, timezone

DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

async def add_test_data():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("🗄️ Adding Test Data to Database")
        print("=" * 60)
        
        # Add test customers
        customers = [
            {
                "customer_code": "C001",
                "invoice_title": "測試客戶一號有限公司",
                "short_name": "測試客戶一",
                "address": "台北市信義區信義路五段7號",
                "phone": "02-27208889",
                "area": "信義區",
                "customer_type": "COMMERCIAL"
            },
            {
                "customer_code": "C002", 
                "invoice_title": "幸福餐廳",
                "short_name": "幸福餐廳",
                "address": "台北市大安區復興南路一段390號",
                "phone": "02-27557788",
                "area": "大安區",
                "customer_type": "RESTAURANT"
            },
            {
                "customer_code": "C003",
                "invoice_title": "王小明",
                "short_name": "王先生",
                "address": "台北市中山區民生東路三段88號5樓",
                "phone": "0912-345678",
                "area": "中山區",
                "customer_type": "RESIDENTIAL"
            }
        ]
        
        for customer in customers:
            try:
                await conn.execute("""
                    INSERT INTO customers (
                        customer_code, invoice_title, short_name, 
                        address, phone, area, customer_type
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (customer_code) DO UPDATE
                    SET invoice_title = $2, short_name = $3, address = $4,
                        phone = $5, area = $6, customer_type = $7
                """, 
                customer["customer_code"],
                customer["invoice_title"],
                customer["short_name"],
                customer["address"],
                customer["phone"],
                customer["area"],
                customer["customer_type"]
                )
                print(f"✅ Added customer: {customer['short_name']}")
            except Exception as e:
                print(f"❌ Error adding customer {customer['short_name']}: {e}")
        
        # Add test drivers
        drivers = [
            {
                "driver_code": "D001",
                "name": "張師傅",
                "phone": "0922-111222",
                "license_number": "A123456789",
                "vehicle_plate": "ABC-1234"
            },
            {
                "driver_code": "D002",
                "name": "李師傅",
                "phone": "0933-222333",
                "license_number": "B987654321",
                "vehicle_plate": "XYZ-5678"
            }
        ]
        
        for driver in drivers:
            try:
                await conn.execute("""
                    INSERT INTO drivers (
                        driver_code, name, phone, license_number, is_active
                    ) VALUES ($1, $2, $3, $4, true)
                    ON CONFLICT (driver_code) DO UPDATE
                    SET name = $2, phone = $3, license_number = $4
                """,
                driver["driver_code"],
                driver["name"],
                driver["phone"],
                driver["license_number"]
                )
                print(f"✅ Added driver: {driver['name']}")
            except Exception as e:
                print(f"❌ Error adding driver {driver['name']}: {e}")
        
        # Add test gas products
        products = [
            {
                "product_code": "GAS-20KG",
                "name": "20公斤瓦斯桶",
                "description": "標準20公斤液化石油氣",
                "unit_price": 800.0,
                "weight_kg": 20.0
            },
            {
                "product_code": "GAS-16KG",
                "name": "16公斤瓦斯桶",
                "description": "標準16公斤液化石油氣",
                "unit_price": 650.0,
                "weight_kg": 16.0
            },
            {
                "product_code": "GAS-50KG",
                "name": "50公斤瓦斯桶",
                "description": "工業用50公斤液化石油氣",
                "unit_price": 1800.0,
                "weight_kg": 50.0
            }
        ]
        
        for product in products:
            try:
                await conn.execute("""
                    INSERT INTO gas_products (
                        product_code, name, description, unit_price,
                        weight_kg, is_active
                    ) VALUES ($1, $2, $3, $4, $5, true)
                    ON CONFLICT (product_code) DO UPDATE
                    SET name = $2, description = $3, unit_price = $4, weight_kg = $5
                """,
                product["product_code"],
                product["name"],
                product["description"],
                product["unit_price"],
                product["weight_kg"]
                )
                print(f"✅ Added product: {product['name']}")
            except Exception as e:
                print(f"❌ Error adding product {product['name']}: {e}")
        
        # Get counts
        customer_count = await conn.fetchval("SELECT COUNT(*) FROM customers")
        driver_count = await conn.fetchval("SELECT COUNT(*) FROM drivers")
        product_count = await conn.fetchval("SELECT COUNT(*) FROM gas_products")
        
        print("\n" + "=" * 60)
        print("📊 Database Summary:")
        print(f"  Customers: {customer_count}")
        print(f"  Drivers: {driver_count}")
        print(f"  Products: {product_count}")
        print("=" * 60)
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_test_data())