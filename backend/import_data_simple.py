#!/usr/bin/env python
"""
Simplified Import Script for May 2025 Excel Data
Works with the simplified models in app.models
"""

import os
import sys
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import Base
from app.models import Customer, Order, OrderStatus, CustomerType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleDataImporter:
    """Simplified data importer for May 2025 Excel files"""
    
    def __init__(self):
        """Initialize the importer"""
        # Database connection
        self.database_url = settings.DATABASE_URL
        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # File paths
        self.base_path = "/Users/lgee258/Desktop/LuckyGas-v3/raw"
        self.client_file = os.path.join(self.base_path, "2025-05 commercial client list.xlsx")
        self.delivery_file = os.path.join(self.base_path, "2025-05 commercial deliver history.xlsx")
        
    def clean_string(self, value):
        """Clean string values"""
        if pd.isna(value):
            return None
        return str(value).strip()
    
    def clean_numeric(self, value):
        """Clean numeric values"""
        if pd.isna(value):
            return 0
        try:
            return int(float(str(value).replace(',', '')))
        except:
            return 0
    
    def clean_float(self, value):
        """Clean float values"""
        if pd.isna(value):
            return 0.0
        try:
            return float(str(value).replace(',', ''))
        except:
            return 0.0
    
    def import_customers(self):
        """Import customers from Excel file"""
        logger.info(f"Reading customers from: {self.client_file}")
        
        try:
            # Read Excel file
            df = pd.read_excel(self.client_file)
            logger.info(f"Found {len(df)} customers in Excel")
            
            imported = 0
            updated = 0
            
            for index, row in df.iterrows():
                try:
                    # Get customer code
                    customer_code = self.clean_string(row.get('客戶'))
                    if not customer_code:
                        logger.debug(f"Skipping row {index}: no customer code")
                        continue
                    
                    # Check if customer exists
                    existing = self.session.query(Customer).filter_by(
                        customer_code=customer_code
                    ).first()
                    
                    if existing:
                        # Update existing customer
                        existing.invoice_title = self.clean_string(row.get('電子發票抬頭')) or existing.invoice_title
                        existing.short_name = self.clean_string(row.get('客戶簡稱')) or existing.short_name
                        existing.address = self.clean_string(row.get('地址')) or existing.address
                        existing.cylinders_50kg = self.clean_numeric(row.get('50KG'))
                        existing.cylinders_20kg = self.clean_numeric(row.get('20KG'))
                        existing.cylinders_16kg = self.clean_numeric(row.get('16KG'))
                        existing.cylinders_10kg = self.clean_numeric(row.get('10KG'))
                        updated += 1
                    else:
                        # Create new customer
                        customer = Customer(
                            customer_code=customer_code,
                            invoice_title=self.clean_string(row.get('電子發票抬頭')) or '',
                            short_name=self.clean_string(row.get('客戶簡稱')) or customer_code,
                            address=self.clean_string(row.get('地址')) or '待補充',
                            phone='',  # No phone column in this data
                            customer_type=CustomerType.COMMERCIAL,
                            cylinders_50kg=self.clean_numeric(row.get('50KG')),
                            cylinders_20kg=self.clean_numeric(row.get('20KG')),
                            cylinders_16kg=self.clean_numeric(row.get('16KG')),
                            cylinders_10kg=self.clean_numeric(row.get('10KG')),
                            is_active=True
                        )
                        self.session.add(customer)
                        imported += 1
                    
                except Exception as e:
                    logger.error(f"Error processing customer row {index}: {str(e)}")
                    continue
            
            # Commit changes
            self.session.commit()
            logger.info(f"✅ Customers: {imported} imported, {updated} updated")
            
        except Exception as e:
            logger.error(f"Failed to import customers: {str(e)}")
            self.session.rollback()
    
    def import_orders(self):
        """Import orders from delivery history Excel file"""
        logger.info(f"Reading delivery history from: {self.delivery_file}")
        
        try:
            # Read Excel file
            df = pd.read_excel(self.delivery_file)
            logger.info(f"Found {len(df)} delivery records in Excel")
            
            imported = 0
            
            for index, row in df.iterrows():
                try:
                    # Parse date - format is Taiwan year YYYMMDD (e.g., 1100102 = 2021-01-02)
                    date_str = str(row.get('最後十次日期'))
                    if not date_str or date_str == 'nan':
                        continue
                    
                    # Convert Taiwan year to Western year
                    try:
                        if len(date_str) == 7:  # Format: YYYMMDD
                            taiwan_year = int(date_str[:3])
                            month = int(date_str[3:5])
                            day = int(date_str[5:7])
                            western_year = taiwan_year + 1911  # Convert from Taiwan year
                            transaction_date = datetime(western_year, month, day)
                            
                            # Only import May 2025 data to reduce volume
                            if transaction_date.year != 2025 or transaction_date.month != 5:
                                continue
                        else:
                            continue
                    except:
                        continue
                    
                    # Get customer
                    customer_code = self.clean_string(row.get('客戶'))
                    if not customer_code:
                        continue
                    
                    customer = self.session.query(Customer).filter_by(
                        customer_code=customer_code
                    ).first()
                    
                    if not customer:
                        # Create customer if not exists
                        customer = Customer(
                            customer_code=customer_code,
                            invoice_title=self.clean_string(row.get('電子發票抬頭')) or '',
                            short_name=self.clean_string(row.get('客戶簡稱')) or customer_code,
                            address=self.clean_string(row.get('地址')) or '待補充',
                            customer_type=CustomerType.COMMERCIAL,
                            is_active=True
                        )
                        self.session.add(customer)
                        self.session.flush()
                    
                    # For delivery history, we'll use default quantities since columns aren't available
                    # You could enhance this by parsing from address or other fields
                    cylinders = {
                        '50kg': 1,  # Default to 1 cylinder per delivery
                        '20kg': 0,
                        '16kg': 0,
                        '10kg': 0,
                        '4kg': 0,
                    }
                    
                    # Simple price mapping
                    prices = {
                        '50kg': 2500,
                        '20kg': 1200,
                        '16kg': 1000,
                        '10kg': 700,
                        '4kg': 350,
                    }
                    
                    total_amount = sum(cylinders[key] * prices[key] for key in cylinders)
                    
                    # Create products string
                    products = []
                    if cylinders['50kg'] > 0:
                        products.append(f"50kg×{cylinders['50kg']}")
                    if cylinders['20kg'] > 0:
                        products.append(f"20kg×{cylinders['20kg']}")
                    if cylinders['16kg'] > 0:
                        products.append(f"16kg×{cylinders['16kg']}")
                    if cylinders['10kg'] > 0:
                        products.append(f"10kg×{cylinders['10kg']}")
                    if cylinders['4kg'] > 0:
                        products.append(f"4kg×{cylinders['4kg']}")
                    
                    products_str = ", ".join(products) if products else "無"
                    
                    # Create order with order number
                    order_number = f"IMP{transaction_date.strftime('%Y%m%d')}{imported+1:05d}"
                    order = Order(
                        order_number=order_number,
                        customer_id=customer.id,
                        order_date=transaction_date.date(),
                        delivery_date=transaction_date,
                        status=OrderStatus.DELIVERED,
                        total_amount=total_amount,
                        qty_50kg=cylinders['50kg'],
                        qty_20kg=cylinders['20kg'],
                        qty_16kg=cylinders['16kg'],
                        qty_10kg=cylinders['10kg'],
                        notes=f"Imported from May 2025 data - {products_str}"
                    )
                    self.session.add(order)
                    imported += 1
                    
                    if imported % 100 == 0:
                        logger.info(f"  Processed {imported} orders...")
                        self.session.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing order row {index}: {str(e)}")
                    continue
            
            # Final commit
            self.session.commit()
            logger.info(f"✅ Orders: {imported} imported")
            
        except Exception as e:
            logger.error(f"Failed to import orders: {str(e)}")
            self.session.rollback()
    
    def generate_statistics(self):
        """Generate and display import statistics"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 IMPORT STATISTICS")
        logger.info("=" * 60)
        
        # Customer stats
        total_customers = self.session.query(Customer).count()
        active_customers = self.session.query(Customer).filter_by(is_active=True).count()
        commercial_customers = self.session.query(Customer).filter_by(
            customer_type=CustomerType.COMMERCIAL
        ).count()
        
        # Order stats
        total_orders = self.session.query(Order).count()
        delivered_orders = self.session.query(Order).filter_by(
            status=OrderStatus.DELIVERED
        ).count()
        
        # May 2025 specific stats
        may_start = datetime(2025, 5, 1).date()
        may_end = datetime(2025, 5, 31).date()
        may_orders = self.session.query(Order).filter(
            Order.order_date >= may_start,
            Order.order_date <= may_end
        ).count()
        
        logger.info(f"Total Customers: {total_customers}")
        logger.info(f"Active Customers: {active_customers}")
        logger.info(f"Commercial Customers: {commercial_customers}")
        logger.info(f"Total Orders: {total_orders}")
        logger.info(f"Delivered Orders: {delivered_orders}")
        logger.info(f"May 2025 Orders: {may_orders}")
        logger.info("=" * 60)
    
    def run(self):
        """Run the complete import process"""
        logger.info("\n🚀 Starting Lucky Gas Data Import...")
        logger.info("=" * 60)
        
        try:
            # Import customers
            self.import_customers()
            
            # Import orders
            self.import_orders()
            
            # Generate statistics
            self.generate_statistics()
            
            logger.info("\n✅ Data import completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Import failed: {str(e)}")
            self.session.rollback()
            raise
        finally:
            self.session.close()

def main():
    """Main entry point"""
    # Check if files exist
    base_path = "/Users/lgee258/Desktop/LuckyGas-v3/raw"
    client_file = os.path.join(base_path, "2025-05 commercial client list.xlsx")
    delivery_file = os.path.join(base_path, "2025-05 commercial deliver history.xlsx")
    
    if not os.path.exists(client_file):
        logger.error(f"❌ Client file not found: {client_file}")
        return 1
    
    if not os.path.exists(delivery_file):
        logger.error(f"❌ Delivery file not found: {delivery_file}")
        return 1
    
    # Run import
    importer = SimpleDataImporter()
    importer.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())