"""
Import customer data from Excel file to PostgreSQL database with comprehensive NaN handling
"""
import asyncio
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from app.core.database import async_session_maker, create_db_and_tables
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings


class DataImportReport:
    """Track import statistics and data quality issues"""
    
    def __init__(self):
        self.total_rows = 0
        self.successful_imports = 0
        self.failed_imports = 0
        self.skipped_existing = 0
        self.nan_replacements: Dict[str, int] = {}
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        
    def add_nan_replacement(self, field: str):
        """Track when NaN values are replaced with defaults"""
        self.nan_replacements[field] = self.nan_replacements.get(field, 0) + 1
        
    def add_error(self, row_index: int, customer_code: str, error: str):
        """Record import errors"""
        self.errors.append({
            'row': row_index,
            'customer_code': customer_code,
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        })
        
    def add_warning(self, row_index: int, customer_code: str, warning: str):
        """Record data quality warnings"""
        self.warnings.append({
            'row': row_index,
            'customer_code': customer_code,
            'warning': warning,
            'timestamp': datetime.now().isoformat()
        })
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive import report"""
        return {
            'summary': {
                'total_rows': self.total_rows,
                'successful_imports': self.successful_imports,
                'failed_imports': self.failed_imports,
                'skipped_existing': self.skipped_existing,
                'success_rate': f"{(self.successful_imports / self.total_rows * 100):.1f}%" if self.total_rows > 0 else "0%"
            },
            'data_quality': {
                'total_nan_replacements': sum(self.nan_replacements.values()),
                'nan_replacements_by_field': self.nan_replacements,
                'fields_with_most_nan': sorted(self.nan_replacements.items(), key=lambda x: x[1], reverse=True)[:10]
            },
            'errors': {
                'total': len(self.errors),
                'details': self.errors[:20]  # First 20 errors
            },
            'warnings': {
                'total': len(self.warnings),
                'details': self.warnings[:20]  # First 20 warnings
            },
            'timestamp': datetime.now().isoformat()
        }


def safe_int(value: Any, default: int = 0, field_name: str = None, report: DataImportReport = None) -> int:
    """Safely convert value to integer with NaN handling"""
    if pd.isna(value):
        if report and field_name:
            report.add_nan_replacement(field_name)
        return default
    try:
        # Handle float to int conversion
        if isinstance(value, float):
            return int(value)
        return int(value)
    except (ValueError, TypeError):
        if report and field_name:
            report.add_nan_replacement(field_name)
        return default


def safe_float(value: Any, default: float = 0.0, field_name: str = None, report: DataImportReport = None) -> float:
    """Safely convert value to float with NaN handling"""
    if pd.isna(value):
        if report and field_name:
            report.add_nan_replacement(field_name)
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        if report and field_name:
            report.add_nan_replacement(field_name)
        return default


def safe_str(value: Any, default: str = '', field_name: str = None, report: DataImportReport = None) -> str:
    """Safely convert value to string with NaN handling"""
    if pd.isna(value):
        if report and field_name:
            report.add_nan_replacement(field_name)
        return default
    return str(value).strip()


def safe_bool(value: Any, default: bool = False, field_name: str = None, report: DataImportReport = None) -> bool:
    """Safely convert value to boolean with NaN handling"""
    if pd.isna(value):
        if report and field_name:
            report.add_nan_replacement(field_name)
        return default
    # Handle various boolean representations
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 't', 'y')
    return default


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
    """Import customers from Excel file with comprehensive NaN handling"""
    # Initialize report
    report = DataImportReport()
    
    # Read Excel file
    excel_path = Path(__file__).parent.parent.parent / "raw" / "2025-05 client liss.xlsx"
    print(f"Reading Excel file: {excel_path}")
    
    try:
        df = pd.read_excel(excel_path)
        report.total_rows = len(df)
        print(f"Found {len(df)} customers in Excel file")
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return
    
    # Create database tables
    await create_db_and_tables()
    
    async with async_session_maker() as session:
        # Create superuser first
        await create_superuser(session)
        
        # Import customers
        for idx, row in df.iterrows():
            try:
                customer_code = safe_str(row.get('客戶', ''), field_name='客戶', report=report)
                
                if not customer_code:
                    report.add_warning(idx, 'Unknown', 'Missing customer code')
                    continue
                
                # Check if customer already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(Customer).where(Customer.customer_code == customer_code)
                )
                if result.scalar_one_or_none():
                    report.skipped_existing += 1
                    continue
                
                # Create customer with comprehensive NaN handling
                customer = Customer(
                    customer_code=customer_code,
                    invoice_title=safe_str(row.get('電子發票抬頭', ''), field_name='電子發票抬頭', report=report),
                    short_name=safe_str(row.get('客戶簡稱', ''), field_name='客戶簡稱', report=report),
                    address=safe_str(row.get('地址', ''), field_name='地址', report=report),
                    
                    # Cylinder quantities - default to 0 (customer doesn't use this type)
                    cylinders_50kg=safe_int(row.get('50KG'), default=0, field_name='50KG', report=report),
                    cylinders_20kg=safe_int(row.get('20KG'), default=0, field_name='20KG', report=report),
                    cylinders_16kg=safe_int(row.get('16KG'), default=0, field_name='16KG', report=report),
                    cylinders_10kg=safe_int(row.get('10KG'), default=0, field_name='10KG', report=report),
                    cylinders_4kg=safe_int(row.get('4KG'), default=0, field_name='4KG', report=report),
                    
                    # Special cylinders - default to 0
                    cylinders_ying20=safe_int(row.get('營20'), default=0, field_name='營20', report=report),
                    cylinders_ying16=safe_int(row.get('營16'), default=0, field_name='營16', report=report),
                    cylinders_haoyun20=safe_int(row.get('好運20'), default=0, field_name='好運20', report=report),
                    cylinders_haoyun16=safe_int(row.get('好運16'), default=0, field_name='好運16', report=report),
                    
                    # Delivery preferences
                    area=safe_str(row.get('區域', ''), field_name='區域', report=report),
                    delivery_type=safe_int(row.get('1汽車/2機車/0全部'), default=0, field_name='1汽車/2機車/0全部', report=report),
                    
                    # Consumption data - sensible defaults
                    avg_daily_usage=safe_float(row.get('平均日使用'), default=0.0, field_name='平均日使用', report=report),
                    max_cycle_days=safe_int(row.get('最大週期'), default=30, field_name='最大週期', report=report),  # Default 30 days
                    can_delay_days=safe_int(row.get('可延後天數'), default=7, field_name='可延後天數', report=report),  # Default 7 days
                    monthly_delivery_volume=safe_float(row.get('月配送量'), default=0.0, field_name='月配送量', report=report),
                    
                    # Pricing
                    pricing_method=safe_str(row.get('計價方式', ''), field_name='計價方式', report=report),
                    payment_method=safe_str(row.get('結帳方式', ''), field_name='結帳方式', report=report),
                    
                    # Status flags - default to False
                    is_subscription=safe_bool(row.get('訂閱式會員'), default=False, field_name='訂閱式會員', report=report),
                    needs_report=safe_bool(row.get('發報'), default=False, field_name='發報', report=report),
                    needs_patrol=safe_bool(row.get('排巡'), default=False, field_name='排巡', report=report),
                    is_equipment_purchased=safe_bool(row.get('設備客戶買斷'), default=False, field_name='設備客戶買斷', report=report),
                    is_terminated=safe_bool(row.get('已解約'), default=False, field_name='已解約', report=report),
                    needs_same_day_delivery=safe_bool(row.get('需要當天配送'), default=False, field_name='需要當天配送', report=report),
                    
                    # Business info
                    closed_days=safe_str(row.get('公休日', ''), field_name='公休日', report=report),
                    
                    # Equipment - default to False
                    regulator_model=safe_str(row.get('切替器型號', ''), field_name='切替器型號', report=report),
                    has_flow_meter=safe_bool(row.get('流量表'), default=False, field_name='流量表', report=report),
                    has_wired_flow_meter=safe_bool(row.get('帶線流量錶'), default=False, field_name='帶線流量錶', report=report),
                    has_regulator=safe_bool(row.get('切替器'), default=False, field_name='切替器', report=report),
                    has_pressure_gauge=safe_bool(row.get('接點式壓力錶'), default=False, field_name='接點式壓力錶', report=report),
                    has_pressure_switch=safe_bool(row.get('壓差開關'), default=False, field_name='壓差開關', report=report),
                    has_micro_switch=safe_bool(row.get('微動開關'), default=False, field_name='微動開關', report=report),
                    has_smart_scale=safe_bool(row.get('智慧秤'), default=False, field_name='智慧秤', report=report),
                    
                    # Customer type
                    customer_type=safe_str(row.get('類型', ''), field_name='類型', report=report)
                )
                
                # Handle delivery time slots
                time_found = False
                for hour in range(8, 20):
                    time_slot = f"{hour}~{hour+1}"
                    if time_slot in df.columns and not pd.isna(row.get(time_slot)):
                        customer.delivery_time_start = f"{hour:02d}:00"
                        customer.delivery_time_end = f"{hour+1:02d}:00"
                        time_found = True
                        break
                
                if not time_found:
                    # Default delivery time 8:00-17:00
                    customer.delivery_time_start = "08:00"
                    customer.delivery_time_end = "17:00"
                
                # Validate critical data
                if not customer.address:
                    report.add_warning(idx, customer_code, 'Missing address')
                
                if customer.avg_daily_usage == 0 and any([
                    customer.cylinders_50kg, customer.cylinders_20kg, 
                    customer.cylinders_16kg, customer.cylinders_10kg, customer.cylinders_4kg
                ]):
                    report.add_warning(idx, customer_code, 'Has cylinders but no daily usage data')
                
                session.add(customer)
                report.successful_imports += 1
                
                # Commit every 100 records
                if report.successful_imports % 100 == 0:
                    await session.commit()
                    print(f"✅ Imported {report.successful_imports} customers...")
                    
            except Exception as e:
                report.failed_imports += 1
                report.add_error(idx, customer_code if 'customer_code' in locals() else 'Unknown', str(e))
                print(f"❌ Error importing row {idx}: {e}")
                continue
        
        # Final commit
        await session.commit()
        
    # Generate and save report
    final_report = report.generate_report()
    
    # Print summary
    print("\n" + "="*60)
    print("📊 IMPORT SUMMARY")
    print("="*60)
    print(f"✅ Successfully imported: {report.successful_imports}")
    print(f"⏭️  Skipped (existing): {report.skipped_existing}")
    print(f"❌ Failed: {report.failed_imports}")
    print(f"📈 Success rate: {final_report['summary']['success_rate']}")
    
    print("\n🔍 DATA QUALITY SUMMARY")
    print(f"Total NaN replacements: {final_report['data_quality']['total_nan_replacements']}")
    print("\nTop 10 fields with NaN replacements:")
    for field, count in final_report['data_quality']['fields_with_most_nan'][:10]:
        print(f"  - {field}: {count} replacements")
    
    if report.warnings:
        print(f"\n⚠️  Total warnings: {len(report.warnings)}")
        print("Sample warnings:")
        for warning in report.warnings[:5]:
            print(f"  - Row {warning['row']} ({warning['customer_code']}): {warning['warning']}")
    
    # Save detailed report to file
    report_path = Path(__file__).parent / f"import_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Detailed report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(import_customers())