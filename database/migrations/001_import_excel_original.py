"""
Import customer data from Excel file to PostgreSQL database
"""
import asyncio
import pandas as pd
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from app.core.database import async_session_maker, create_db_and_tables
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings


async def create_superuser(session: AsyncSession):
    """Create the first superuser if it doesn't exist"""
    from sqlalchemy import select
    
    result = await session.execute(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    )
    if not result.scalar_one_or_none():
        superuser = User(
            email=settings.FIRST_SUPERUSER,
            username=settings.FIRST_SUPERUSER.split('@')[0],
            full_name="System Administrator",
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        session.add(superuser)
        await session.commit()
        print(f"Created superuser: {settings.FIRST_SUPERUSER}")


async def import_customers():
    """Import customers from Excel file"""
    # Read Excel file
    excel_path = Path(__file__).parent.parent.parent / "raw" / "2025-05 client liss.xlsx"
    print(f"Reading Excel file: {excel_path}")
    
    df = pd.read_excel(excel_path)
    print(f"Found {len(df)} customers in Excel file")
    
    # Create database tables
    await create_db_and_tables()
    
    async with async_session_maker() as session:
        # Create superuser first
        await create_superuser(session)
        
        # Import customers
        customers_added = 0
        customers_skipped = 0
        
        for idx, row in df.iterrows():
            try:
                # Check if customer already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(Customer).where(Customer.customer_code == str(row['客戶']))
                )
                if result.scalar_one_or_none():
                    customers_skipped += 1
                    continue
                
                # Create customer
                customer = Customer(
                    customer_code=str(row['客戶']),
                    invoice_title=row.get('電子發票抬頭', ''),
                    short_name=row.get('客戶簡稱', ''),
                    address=row.get('地址', ''),
                    
                    # Cylinder quantities
                    cylinders_50kg=int(row.get('50KG', 0) or 0),
                    cylinders_20kg=int(row.get('20KG', 0) or 0),
                    cylinders_16kg=int(row.get('16KG', 0) or 0),
                    cylinders_10kg=int(row.get('10KG', 0) or 0),
                    cylinders_4kg=int(row.get('4KG', 0) or 0),
                    
                    # Special cylinders
                    cylinders_ying20=int(row.get('營20', 0) or 0),
                    cylinders_ying16=int(row.get('營16', 0) or 0),
                    cylinders_haoyun20=int(row.get('好運20', 0) or 0),
                    cylinders_haoyun16=int(row.get('好運16', 0) or 0),
                    
                    # Delivery preferences
                    area=row.get('區域', ''),
                    delivery_type=int(row.get('1汽車/2機車/0全部', 0) or 0),
                    
                    # Consumption data
                    avg_daily_usage=float(row.get('平均日使用', 0) or 0),
                    max_cycle_days=int(row.get('最大週期', 0) or 0),
                    can_delay_days=int(row.get('可延後天數', 0) or 0),
                    monthly_delivery_volume=float(row.get('月配送量', 0) or 0),
                    
                    # Pricing
                    pricing_method=str(row.get('計價方式', '') or ''),
                    payment_method=str(row.get('結帳方式', '') or ''),
                    
                    # Status flags
                    is_subscription=bool(row.get('訂閱式會員', 0)),
                    needs_report=bool(row.get('發報', 0)),
                    needs_patrol=bool(row.get('排巡', 0)),
                    is_equipment_purchased=bool(row.get('設備客戶買斷', 0)),
                    is_terminated=bool(row.get('已解約', 0)),
                    needs_same_day_delivery=bool(row.get('需要當天配送', 0)),
                    
                    # Business info
                    closed_days=str(row.get('公休日', '') or ''),
                    
                    # Equipment
                    regulator_model=str(row.get('切替器型號', '') or ''),
                    has_flow_meter=bool(row.get('流量表', 0)),
                    has_wired_flow_meter=bool(row.get('帶線流量錶', 0)),
                    has_regulator=bool(row.get('切替器', 0)),
                    has_pressure_gauge=bool(row.get('接點式壓力錶', 0)),
                    has_pressure_switch=bool(row.get('壓差開關', 0)),
                    has_micro_switch=bool(row.get('微動開關', 0)),
                    has_smart_scale=bool(row.get('智慧秤', 0)),
                    
                    # Customer type
                    customer_type=str(row.get('類型', '') or '')
                )
                
                # Handle delivery time slots
                for hour in range(8, 20):
                    time_slot = f"{hour}~{hour+1}"
                    if row.get(time_slot):
                        customer.delivery_time_start = f"{hour:02d}:00"
                        customer.delivery_time_end = f"{hour+1:02d}:00"
                        break
                
                session.add(customer)
                customers_added += 1
                
                # Commit every 100 records
                if customers_added % 100 == 0:
                    await session.commit()
                    print(f"Imported {customers_added} customers...")
                    
            except Exception as e:
                print(f"Error importing customer {row.get('客戶', 'Unknown')}: {e}")
                continue
        
        # Final commit
        await session.commit()
        
        print(f"\nImport completed!")
        print(f"Customers added: {customers_added}")
        print(f"Customers skipped (already exist): {customers_skipped}")


if __name__ == "__main__":
    asyncio.run(import_customers())