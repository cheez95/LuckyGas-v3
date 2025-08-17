"""
Import customer and delivery data from Excel files to database
For Lucky Gas commercial client list and delivery history
"""
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, init_db
from app.models import Customer, CustomerType, Delivery, Order, OrderStatus, Route
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_customers_from_excel(file_path: str, db: Session):
    """Import customers from Excel file with Taiwan-specific fields"""
    logger.info(f"Reading customer data from {file_path}")
    
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Found {len(df)} customers in Excel file")
        
        # Print column names to understand the structure
        logger.info(f"Excel columns: {df.columns.tolist()}")
        
        imported = 0
        skipped = 0
        
        for index, row in df.iterrows():
            try:
                # Map Excel columns to database fields
                # Adjust these based on actual Excel column names
                customer_code = str(row.get('客戶代碼', f'CUST{index:04d}'))
                
                # Check if customer already exists
                existing = db.query(Customer).filter_by(customer_code=customer_code).first()
                if existing:
                    skipped += 1
                    continue
                
                # Determine customer type based on name or other criteria
                customer_type = CustomerType.COMMERCIAL
                customer_name = str(row.get('客戶名稱', ''))
                if '餐廳' in customer_name or '飯店' in customer_name:
                    customer_type = CustomerType.RESTAURANT
                elif '工廠' in customer_name or '工業' in customer_name:
                    customer_type = CustomerType.INDUSTRIAL
                
                customer = Customer(
                    customer_code=customer_code,
                    invoice_title=row.get('發票抬頭', customer_name),
                    short_name=row.get('簡稱', customer_name[:20] if customer_name else ''),
                    address=str(row.get('地址', '')),
                    phone=str(row.get('電話', '')),
                    area=str(row.get('區域', '')),
                    customer_type=customer_type,
                    # Gas cylinder counts
                    cylinders_50kg=int(row.get('50公斤桶數', 0) if pd.notna(row.get('50公斤桶數')) else 0),
                    cylinders_20kg=int(row.get('20公斤桶數', 0) if pd.notna(row.get('20公斤桶數')) else 0),
                    cylinders_16kg=int(row.get('16公斤桶數', 0) if pd.notna(row.get('16公斤桶數')) else 0),
                    cylinders_10kg=int(row.get('10公斤桶數', 0) if pd.notna(row.get('10公斤桶數')) else 0),
                    is_active=True
                )
                
                db.add(customer)
                imported += 1
                
                if imported % 10 == 0:
                    logger.info(f"Imported {imported} customers...")
                    
            except Exception as e:
                logger.error(f"Error importing customer at row {index}: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Successfully imported {imported} customers, skipped {skipped} existing")
        return imported
        
    except Exception as e:
        logger.error(f"Failed to import customers: {e}")
        db.rollback()
        raise

def import_delivery_history(file_path: str, db: Session):
    """Import delivery history from Excel file"""
    logger.info(f"Reading delivery history from {file_path}")
    
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Found {len(df)} delivery records in Excel file")
        
        # Print column names to understand the structure
        logger.info(f"Excel columns: {df.columns.tolist()}")
        
        imported = 0
        
        for index, row in df.iterrows():
            try:
                # Parse delivery date
                delivery_date = pd.to_datetime(row.get('配送日期', datetime.now()))
                if pd.isna(delivery_date):
                    delivery_date = datetime.now()
                
                # Get customer
                customer_code = str(row.get('客戶代碼', ''))
                customer = db.query(Customer).filter_by(customer_code=customer_code).first()
                
                if not customer:
                    # Create a basic customer if not found
                    customer = Customer(
                        customer_code=customer_code,
                        short_name=str(row.get('客戶名稱', f'Customer {customer_code}')),
                        invoice_title=str(row.get('客戶名稱', '')),
                        address='地址待更新',
                        customer_type=CustomerType.COMMERCIAL,
                        is_active=True
                    )
                    db.add(customer)
                    db.flush()
                
                # Create order record
                order = Order(
                    order_number=f"ORDER-{datetime.now().strftime('%Y%m%d')}-{index:05d}",
                    customer_id=customer.id,
                    order_date=delivery_date,
                    delivery_date=delivery_date,
                    status=OrderStatus.DELIVERED,
                    qty_50kg=int(row.get('50公斤數量', 0) if pd.notna(row.get('50公斤數量')) else 0),
                    qty_20kg=int(row.get('20公斤數量', 0) if pd.notna(row.get('20公斤數量')) else 0),
                    qty_16kg=int(row.get('16公斤數量', 0) if pd.notna(row.get('16公斤數量')) else 0),
                    qty_10kg=0,  # Not in Excel, default to 0
                    total_amount=float(row.get('總金額', 0) if pd.notna(row.get('總金額')) else 0),
                    notes=str(row.get('備註', ''))
                )
                
                db.add(order)
                db.flush()  # Flush to get order.id
                
                # Create delivery record
                delivery = Delivery(
                    order_id=order.id,
                    delivered_at=delivery_date,
                    delivered_50kg=int(row.get('50公斤數量', 0) if pd.notna(row.get('50公斤數量')) else 0),
                    delivered_20kg=int(row.get('20公斤數量', 0) if pd.notna(row.get('20公斤數量')) else 0),
                    delivered_16kg=int(row.get('16公斤數量', 0) if pd.notna(row.get('16公斤數量')) else 0),
                    delivered_10kg=0,
                    is_successful=True,
                    notes=str(row.get('備註', ''))
                )
                
                db.add(delivery)
                imported += 1
                
                if imported % 50 == 0:
                    logger.info(f"Imported {imported} delivery records...")
                    
            except Exception as e:
                logger.error(f"Error importing delivery at row {index}: {e}")
                continue
        
        db.commit()
        logger.info(f"✅ Successfully imported {imported} delivery records")
        return imported
        
    except Exception as e:
        logger.error(f"Failed to import deliveries: {e}")
        db.rollback()
        raise

def create_sample_data(db: Session):
    """Create sample data if no Excel files are available"""
    logger.info("Creating sample customer and delivery data...")
    
    # Sample customers
    sample_customers = [
        {
            'customer_code': 'REST001',
            'invoice_title': '幸福餐廳',
            'short_name': '幸福餐廳',
            'address': '台北市中正區重慶南路一段122號',
            'phone': '02-2345-6789',
            'area': '中正區',
            'customer_type': CustomerType.RESTAURANT,
            'cylinders_20kg': 2,
            'cylinders_50kg': 1
        },
        {
            'customer_code': 'IND001',
            'invoice_title': '大同工廠股份有限公司',
            'short_name': '大同工廠',
            'address': '新北市三重區重新路五段609巷4號',
            'phone': '02-8765-4321',
            'area': '三重區',
            'customer_type': CustomerType.INDUSTRIAL,
            'cylinders_50kg': 5
        },
        {
            'customer_code': 'COM001',
            'invoice_title': '台北辦公大樓',
            'short_name': '台北辦公',
            'address': '台北市信義區信義路五段7號',
            'phone': '02-2720-1234',
            'area': '信義區',
            'customer_type': CustomerType.COMMERCIAL,
            'cylinders_20kg': 3
        }
    ]
    
    created_customers = []
    for cust_data in sample_customers:
        existing = db.query(Customer).filter_by(customer_code=cust_data['customer_code']).first()
        if not existing:
            customer = Customer(**cust_data, is_active=True)
            db.add(customer)
            created_customers.append(customer)
    
    db.flush()
    
    # Create sample orders and deliveries
    from datetime import timedelta
    today = datetime.now()
    
    for customer in created_customers:
        for days_ago in [1, 7, 14, 21, 28]:
            order_date = today - timedelta(days=days_ago)
            
            order = Order(
                order_number=f"ORDER-{order_date.strftime('%Y%m%d')}-{customer.id:03d}-{days_ago:03d}",
                customer_id=customer.id,
                order_date=order_date,
                delivery_date=order_date,
                status=OrderStatus.DELIVERED,
                qty_20kg=customer.cylinders_20kg or 0,
                qty_50kg=customer.cylinders_50kg or 0,
                qty_16kg=customer.cylinders_16kg or 0,
                qty_10kg=customer.cylinders_10kg or 0,
                total_amount=(customer.cylinders_20kg or 0) * 750 + (customer.cylinders_50kg or 0) * 1800,
                notes=f'定期配送 - {days_ago}天前'
            )
            db.add(order)
    
    db.commit()
    logger.info(f"✅ Created {len(created_customers)} sample customers with orders")

def main():
    """Main import function"""
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Check for Excel files
        customer_file = "raw/2025-05 commercial client list.xlsx"
        delivery_file = "raw/2025-05 commercial deliver history.xlsx"
        
        if os.path.exists(customer_file):
            import_customers_from_excel(customer_file, db)
        else:
            logger.warning(f"Customer file not found: {customer_file}")
        
        if os.path.exists(delivery_file):
            import_delivery_history(delivery_file, db)
        else:
            logger.warning(f"Delivery file not found: {delivery_file}")
        
        # If no Excel files, create sample data
        if not os.path.exists(customer_file) and not os.path.exists(delivery_file):
            logger.info("No Excel files found, creating sample data...")
            create_sample_data(db)
        
        logger.info("✅ Data import completed successfully!")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()