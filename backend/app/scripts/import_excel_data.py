#!/usr/bin/env python3
"""
Import client list and delivery history from Excel files into PostgreSQL database
"""
import asyncio
import logging
# Add project root to Python path
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import async_session_maker, engine
from app.models.customer import Customer
from app.models.delivery_history import DeliveryHistory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File paths
RAW_DIR = project_root.parent / 'raw'
CLIENT_FILE = RAW_DIR / '2025-05 client liss.xlsx'
DELIVERY_FILE = RAW_DIR / '2025-05 deliver history.xlsx'


def clean_numeric(value):
    """Clean numeric values, handling NaN and converting to appropriate type"""
    if pd.isna(value):
        return None
    if isinstance(value, str):
        # Remove any non-numeric characters
        value = ''.join(filter(lambda x: x.isdigit() or x == '.', value))
        if not value:
            return None
    try:
        if '.' in str(value):
            return float(value)
        return int(value)
    except:
        return None


def clean_boolean(value):
    """Convert various representations to boolean"""
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.upper() in ['V', 'Y', 'YES', 'TRUE', '1']
    return bool(value)


async def import_customers(session: AsyncSession):
    """Import customers from Excel file"""
    logger.info(f"Reading customer data from {CLIENT_FILE}")
    
    # Read the main customer sheet
    df = pd.read_excel(CLIENT_FILE, sheet_name='客戶資料')
    logger.info(f"Found {len(df)} customers in Excel file")
    
    # Map Excel columns to model fields
    imported_count = 0
    updated_count = 0
    
    for idx, row in df.iterrows():
        try:
            # Skip rows without customer ID
            customer_id = clean_numeric(row['客戶'])
            if not customer_id:
                continue
            
            # Check if customer already exists
            stmt = select(Customer).where(Customer.customer_code == str(customer_id))
            result = await session.execute(stmt)
            existing_customer = result.scalar_one_or_none()
            
            # Prepare customer data
            customer_data = {
                'customer_code': str(customer_id),
                'invoice_title': str(row['電子發票抬頭']) if pd.notna(row['電子發票抬頭']) else None,
                'short_name': str(row['客戶簡稱']) if pd.notna(row['客戶簡稱']) else f"Customer {customer_id}",
                'address': str(row['地址']) if pd.notna(row['地址']) else '',
                
                # Cylinder inventory
                'cylinders_50kg': clean_numeric(row.get('50KG', 0)) or 0,
                'cylinders_20kg': clean_numeric(row.get('20KG', 0)) or 0,
                'cylinders_16kg': clean_numeric(row.get('16KG', 0)) or 0,
                'cylinders_10kg': clean_numeric(row.get('10KG', 0)) or 0,
                'cylinders_4kg': clean_numeric(row.get('4KG', 0)) or 0,
                'cylinders_ying20': clean_numeric(row.get('營20', 0)) or 0,
                'cylinders_ying16': clean_numeric(row.get('營16', 0)) or 0,
                'cylinders_haoyun20': clean_numeric(row.get('好運20', 0)) or 0,
                'cylinders_haoyun16': clean_numeric(row.get('好運16', 0)) or 0,
                
                # Delivery preferences
                'area': str(row['區域']) if pd.notna(row['區域']) else None,
                'delivery_time_slot': clean_numeric(row.get('時段早1午2晚3全天0', 0)),
                'delivery_type': clean_numeric(row.get('1汽車/2機車/0全部', 0)) or 0,
                
                # Consumption data
                'avg_daily_usage': clean_numeric(row.get('平均日使用')),
                'max_cycle_days': clean_numeric(row.get('最大週期')),
                'can_delay_days': clean_numeric(row.get('可延後天數')),
                'monthly_delivery_volume': clean_numeric(row.get('月配送量')),
                
                # Pricing and payment
                'pricing_method': str(row['計價方式']) if pd.notna(row['計價方式']) else None,
                'payment_method': str(row['結帳方式']) if pd.notna(row['結帳方式']) else None,
                
                # Status flags
                'is_subscription': clean_boolean(row.get('訂閱式會員')),
                'needs_report': clean_boolean(row.get('發報')),
                'needs_patrol': clean_boolean(row.get('排巡')),
                'is_equipment_purchased': pd.notna(row.get('設備客戶買斷')),
                'is_terminated': clean_boolean(row.get('已解約')),
                'needs_same_day_delivery': clean_boolean(row.get('需要當天配送')),
                
                # Business days
                'closed_days': str(row['公休日']) if pd.notna(row['公休日']) else None,
                
                # Equipment
                'regulator_model': str(row['切替器型號']) if pd.notna(row['切替器型號']) else None,
                'has_flow_meter': clean_boolean(row.get('流量表')),
                'has_regulator': clean_boolean(row.get('切替器')),
                'has_pressure_gauge': clean_boolean(row.get('接點式壓力錶')),
                'has_pressure_switch': clean_boolean(row.get('壓差開關')),
                'has_micro_switch': clean_boolean(row.get('微動開關')),
                'has_smart_scale': clean_boolean(row.get('智慧秤')),
                
                # Customer type
                'customer_type': str(row['類型']) if pd.notna(row['類型']) else None,
            }
            
            # Extract delivery time preferences
            for hour in range(8, 21):  # 8:00 to 20:00
                col_name = f'{hour}~{hour+1}'
                if col_name in row and clean_boolean(row[col_name]):
                    customer_data['delivery_time_start'] = f"{hour:02d}:00"
                    customer_data['delivery_time_end'] = f"{hour+1:02d}:00"
                    break
            
            if existing_customer:
                # Update existing customer
                for key, value in customer_data.items():
                    setattr(existing_customer, key, value)
                updated_count += 1
                logger.debug(f"Updated customer {customer_id}")
            else:
                # Create new customer
                new_customer = Customer(**customer_data)
                session.add(new_customer)
                imported_count += 1
                logger.debug(f"Imported new customer {customer_id}")
            
            # Commit every 100 records
            if (idx + 1) % 100 == 0:
                await session.commit()
                logger.info(f"Progress: {idx + 1}/{len(df)} customers processed")
                
        except Exception as e:
            logger.error(f"Error processing customer at row {idx}: {e}")
            continue
    
    # Final commit
    await session.commit()
    logger.info(f"Customer import complete: {imported_count} new, {updated_count} updated")
    return imported_count, updated_count


async def import_delivery_history(session: AsyncSession):
    """Import delivery history from Excel file"""
    logger.info(f"Reading delivery history from {DELIVERY_FILE}")
    
    # Get all sheets
    xl_file = pd.ExcelFile(DELIVERY_FILE)
    total_imported = 0
    
    for sheet_name in xl_file.sheet_names:
        logger.info(f"Processing sheet: {sheet_name}")
        df = pd.read_excel(DELIVERY_FILE, sheet_name=sheet_name)
        
        # Skip empty sheets
        if len(df) == 0:
            continue
        
        imported_count = 0
        
        for idx, row in df.iterrows():
            try:
                # Skip rows without essential data
                customer_code = row.get('客戶編號') or row.get('編號')
                if pd.isna(customer_code):
                    continue
                
                customer_code = str(int(customer_code)) if not pd.isna(customer_code) else None
                if not customer_code:
                    continue
                
                # Find customer in database
                stmt = select(Customer).where(Customer.customer_code == customer_code)
                result = await session.execute(stmt)
                customer = result.scalar_one_or_none()
                
                if not customer:
                    logger.warning(f"Customer {customer_code} not found in database")
                    continue
                
                # Parse transaction date
                trans_date = None
                if '交易日期' in row:
                    date_val = row['交易日期']
                    if pd.notna(date_val):
                        try:
                            # Handle different date formats
                            if isinstance(date_val, (int, float)):
                                # Assuming format like 1140520 (year 114 = 2025, month 05, day 20)
                                date_str = str(int(date_val))
                                if len(date_str) >= 6:
                                    year = int(date_str[:3]) + 1911  # Convert from ROC year
                                    month = int(date_str[3:5])
                                    day = int(date_str[5:7])
                                    trans_date = date(year, month, day)
                            elif isinstance(date_val, datetime):
                                trans_date = date_val.date()
                            else:
                                trans_date = pd.to_datetime(date_val).date()
                        except:
                            logger.warning(f"Could not parse date: {date_val}")
                            continue
                
                if not trans_date:
                    # Try to infer from sheet name
                    if 'Sheet' in sheet_name and sheet_name[-1].isdigit():
                        # Assume May 2025 data
                        day = 20 - int(sheet_name[-1]) + 1
                        trans_date = date(2025, 5, day)
                    else:
                        continue
                
                # Create delivery history record
                history_data = {
                    'transaction_date': trans_date,
                    'transaction_time': str(row.get('交易時間', '')) if pd.notna(row.get('交易時間')) else None,
                    'salesperson': str(row.get('業務員', '')) if pd.notna(row.get('業務員')) else None,
                    'customer_id': customer.id,
                    'customer_code': customer_code,
                    
                    # Cylinder quantities
                    'qty_50kg': clean_numeric(row.get('50公斤', 0)) or 0,
                    'qty_ying20': clean_numeric(row.get('丙烷20', 0)) or 0,
                    'qty_ying16': clean_numeric(row.get('丙烷16', 0)) or 0,
                    'qty_20kg': clean_numeric(row.get('20公斤', 0)) or 0,
                    'qty_16kg': clean_numeric(row.get('16公斤', 0)) or 0,
                    'qty_10kg': clean_numeric(row.get('10公斤', 0)) or 0,
                    'qty_4kg': clean_numeric(row.get('4公斤', 0)) or 0,
                    'qty_haoyun16': clean_numeric(row.get('好運桶16', 0)) or 0,
                    'qty_pingantong10': clean_numeric(row.get('瓶安桶10', 0)) or 0,
                    'qty_xingfuwan4': clean_numeric(row.get('幸福丸4', 0)) or 0,
                    'qty_haoyun20': clean_numeric(row.get('好運桶20', 0)) or 0,
                    
                    # Flow quantities
                    'flow_50kg': clean_numeric(row.get('流量50公斤', 0)) or 0,
                    'flow_20kg': clean_numeric(row.get('流量20公斤', 0)) or 0,
                    'flow_16kg': clean_numeric(row.get('流量16公斤', 0)) or 0,
                    'flow_haoyun20kg': clean_numeric(row.get('流量好運20公斤', 0)) or 0,
                    'flow_haoyun16kg': clean_numeric(row.get('流量好運16公斤', 0)) or 0,
                    
                    # Metadata
                    'source_file': DELIVERY_FILE.name,
                    'source_sheet': sheet_name,
                }
                
                # Calculate total weight and cylinders
                total_weight = (
                    (history_data['qty_50kg'] * 50) +
                    (history_data['qty_ying20'] * 20) +
                    (history_data['qty_ying16'] * 16) +
                    (history_data['qty_20kg'] * 20) +
                    (history_data['qty_16kg'] * 16) +
                    (history_data['qty_10kg'] * 10) +
                    (history_data['qty_4kg'] * 4) +
                    (history_data['qty_haoyun20'] * 20) +
                    (history_data['qty_haoyun16'] * 16) +
                    (history_data['qty_pingantong10'] * 10) +
                    (history_data['qty_xingfuwan4'] * 4) +
                    history_data['flow_50kg'] +
                    history_data['flow_20kg'] +
                    history_data['flow_16kg'] +
                    history_data['flow_haoyun20kg'] +
                    history_data['flow_haoyun16kg']
                )
                
                total_cylinders = sum([
                    history_data['qty_50kg'],
                    history_data['qty_ying20'],
                    history_data['qty_ying16'],
                    history_data['qty_20kg'],
                    history_data['qty_16kg'],
                    history_data['qty_10kg'],
                    history_data['qty_4kg'],
                    history_data['qty_haoyun20'],
                    history_data['qty_haoyun16'],
                    history_data['qty_pingantong10'],
                    history_data['qty_xingfuwan4'],
                ])
                
                history_data['total_weight_kg'] = total_weight
                history_data['total_cylinders'] = total_cylinders
                
                # Skip records with no actual delivery
                if total_weight == 0 and total_cylinders == 0:
                    continue
                
                # Check if record already exists
                stmt = select(DeliveryHistory).where(
                    (DeliveryHistory.customer_code == customer_code) &
                    (DeliveryHistory.transaction_date == trans_date)
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    logger.debug(f"Delivery history already exists for {customer_code} on {trans_date}")
                    continue
                
                # Create new record
                new_history = DeliveryHistory(**history_data)
                session.add(new_history)
                imported_count += 1
                
                # Commit every 100 records
                if imported_count % 100 == 0:
                    await session.commit()
                    logger.info(f"Progress: {imported_count} delivery records imported from {sheet_name}")
                    
            except Exception as e:
                logger.error(f"Error processing delivery history at row {idx} in {sheet_name}: {e}")
                continue
        
        # Commit remaining records
        await session.commit()
        logger.info(f"Imported {imported_count} delivery records from {sheet_name}")
        total_imported += imported_count
    
    logger.info(f"Delivery history import complete: {total_imported} total records")
    return total_imported


async def main():
    """Main import function"""
    logger.info("Starting data import process...")
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        from app.core.database import Base
        await conn.run_sync(Base.metadata.create_all)
    
    # Import data
    async with async_session_maker() as session:
        try:
            # Import customers first
            customer_new, customer_updated = await import_customers(session)
            
            # Import delivery history
            delivery_count = await import_delivery_history(session)
            
            logger.info("\n" + "="*60)
            logger.info("IMPORT SUMMARY")
            logger.info("="*60)
            logger.info(f"Customers: {customer_new} new, {customer_updated} updated")
            logger.info(f"Delivery History: {delivery_count} records imported")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())