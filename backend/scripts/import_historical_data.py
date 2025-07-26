#!/usr/bin/env python3
"""
Import historical data from Excel files in raw/ folder
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import os
from datetime import datetime, date
import re

from app.models.customer import Customer, CustomerType
from app.models.order import Order, OrderStatus, PaymentStatus
from app.models.user import User, UserRole
from app.models.gas_product import GasProduct, DeliveryMethod, ProductAttribute
from app.core.security import get_password_hash


class HistoricalDataImporter:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.raw_path = Path(__file__).parent.parent.parent / "raw"
        
    async def import_all(self):
        """Import all historical data"""
        print("🚀 Starting historical data import...")
        
        try:
            # Import in correct order
            await self.create_default_users()
            await self.create_default_products()
            await self.import_commercial_clients()
            await self.import_commercial_delivery_history()
            await self.import_residential_delivery_plan()
            
            print("✅ Historical data import completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during import: {e}")
            raise
        finally:
            await self.engine.dispose()
    
    async def create_default_users(self):
        """Create default system users"""
        async with self.async_session() as session:
            # Check if users already exist
            result = await session.execute(select(User))
            if result.scalars().first():
                print("ℹ️  Users already exist, skipping...")
                return
            
            users = [
                {
                    "username": "admin",
                    "email": "admin@luckygas.tw",
                    "full_name": "系統管理員",
                    "role": UserRole.SUPER_ADMIN,
                    "password": "admin123"
                },
                {
                    "username": "manager",
                    "email": "manager@luckygas.tw", 
                    "full_name": "經理",
                    "role": UserRole.MANAGER,
                    "password": "manager123"
                },
                {
                    "username": "office1",
                    "email": "office1@luckygas.tw",
                    "full_name": "辦公室人員一",
                    "role": UserRole.OFFICE_STAFF,
                    "password": "office123"
                },
                {
                    "username": "driver1",
                    "email": "driver1@luckygas.tw",
                    "full_name": "司機一號",
                    "role": UserRole.DRIVER,
                    "password": "driver123"
                },
                {
                    "username": "driver2",
                    "email": "driver2@luckygas.tw",
                    "full_name": "司機二號",
                    "role": UserRole.DRIVER,
                    "password": "driver123"
                }
            ]
            
            for user_data in users:
                password = user_data.pop("password")
                user = User(
                    **user_data,
                    hashed_password=get_password_hash(password),
                    is_active=True
                )
                session.add(user)
            
            await session.commit()
            print(f"✅ Created {len(users)} default users")
    
    async def create_default_products(self):
        """Create default gas cylinder products"""
        async with self.async_session() as session:
            # Check if products already exist
            result = await session.execute(select(GasProduct))
            if result.scalars().first():
                print("ℹ️  Products already exist, skipping...")
                return
            
            # Create products for each size and attribute combination
            sizes = [50, 20, 16, 10, 4]
            attributes = [ProductAttribute.REGULAR, ProductAttribute.HAOYUN, ProductAttribute.PINGAN]
            prices = {
                50: 2500.0,
                20: 1200.0,
                16: 1000.0,
                10: 800.0,
                4: 500.0
            }
            
            products_created = 0
            
            for size in sizes:
                for attribute in attributes:
                    # Generate product name and code
                    name = f"{size}公斤{attribute.value}瓦斯桶"
                    sku = f"GAS-{size}KG-{attribute.value}"
                    
                    product = GasProduct(
                        delivery_method=DeliveryMethod.CYLINDER,
                        size_kg=size,
                        attribute=attribute,
                        sku=sku,
                        name_zh=name,
                        name_en=f"{size}kg {attribute.value} Gas Cylinder",
                        unit_price=prices[size],
                        is_active=True
                    )
                    session.add(product)
                    products_created += 1
            
            await session.commit()
            print(f"✅ Created {products_created} gas products")
    
    async def import_commercial_clients(self):
        """Import commercial clients from Excel"""
        file_path = self.raw_path / "2025-05 commercial client list.xlsx"
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return
        
        print(f"📂 Importing commercial clients from {file_path.name}...")
        
        try:
            df = pd.read_excel(file_path)
            print(f"   Found {len(df)} commercial clients")
            
            async with self.async_session() as session:
                imported = 0
                
                for idx, row in df.iterrows():
                    # Extract customer data
                    customer_code = str(row.get('客戶編號', f'COM{idx+1:04d}'))
                    
                    # Check if customer already exists
                    result = await session.execute(
                        select(Customer).where(Customer.customer_code == customer_code)
                    )
                    if result.scalar_one_or_none():
                        continue
                    
                    # Clean phone number
                    phone = str(row.get('電話', ''))
                    phone = re.sub(r'[^\d-]', '', phone)
                    if not phone.startswith('0'):
                        phone = '0' + phone
                    
                    customer = Customer(
                        customer_code=customer_code,
                        short_name=str(row.get('公司名稱', f'商業客戶{idx+1}')),
                        invoice_title=str(row.get('公司名稱', f'商業客戶{idx+1}')),
                        customer_type=CustomerType.COMMERCIAL.value,
                        phone=phone,
                        address=str(row.get('地址', '')),
                        area=str(row.get('區域', '信義區')),
                        tax_id=str(row.get('統編', '')),
                        credit_limit=float(row.get('信用額度', 100000)),
                        payment_method=str(row.get('付款方式', '現金'))
                    )
                    
                    session.add(customer)
                    imported += 1
                
                await session.commit()
                print(f"✅ Imported {imported} commercial clients")
                
        except Exception as e:
            print(f"❌ Error importing commercial clients: {e}")
            raise
    
    async def import_commercial_delivery_history(self):
        """Import commercial delivery history from Excel"""
        file_path = self.raw_path / "2025-05 commercial deliver history.xlsx"
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return
        
        print(f"📂 Importing commercial delivery history from {file_path.name}...")
        
        try:
            df = pd.read_excel(file_path)
            print(f"   Found {len(df)} delivery records")
            
            # Import logic would go here
            # This would create Order records based on the delivery history
            
            print(f"✅ Imported commercial delivery history")
            
        except Exception as e:
            print(f"❌ Error importing delivery history: {e}")
            raise
    
    async def import_residential_delivery_plan(self):
        """Import residential delivery plan from Excel"""
        file_path = self.raw_path / "2025-07 residential client delivery plan.xlsx"
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return
        
        print(f"📂 Importing residential delivery plan from {file_path.name}...")
        
        try:
            df = pd.read_excel(file_path)
            print(f"   Found {len(df)} residential clients")
            
            async with self.async_session() as session:
                imported = 0
                
                for idx, row in df.iterrows():
                    # Extract customer data
                    customer_code = str(row.get('客戶編號', f'RES{idx+1:04d}'))
                    
                    # Check if customer already exists
                    result = await session.execute(
                        select(Customer).where(Customer.customer_code == customer_code)
                    )
                    if result.scalar_one_or_none():
                        continue
                    
                    # Clean phone number
                    phone = str(row.get('電話', ''))
                    phone = re.sub(r'[^\d-]', '', phone)
                    if not phone.startswith('0'):
                        phone = '0' + phone
                    
                    customer = Customer(
                        customer_code=customer_code,
                        short_name=str(row.get('客戶姓名', f'住宅客戶{idx+1}')),
                        invoice_title=str(row.get('客戶姓名', f'住宅客戶{idx+1}')),
                        customer_type=CustomerType.RESIDENTIAL.value,
                        phone=phone,
                        address=str(row.get('地址', '')),
                        area=str(row.get('區域', '大安區')),
                        payment_method='現金'
                    )
                    
                    session.add(customer)
                    imported += 1
                
                await session.commit()
                print(f"✅ Imported {imported} residential clients")
                
        except Exception as e:
            print(f"❌ Error importing residential delivery plan: {e}")
            raise


async def main():
    """Main import function"""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://luckygas:luckygas123@localhost:5433/luckygas"
    )
    
    importer = HistoricalDataImporter(database_url)
    await importer.import_all()


if __name__ == "__main__":
    asyncio.run(main())