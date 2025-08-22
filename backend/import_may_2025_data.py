#!/usr/bin/env python
"""
Import May 2025 Excel Data into Lucky Gas Database
This script imports customer and delivery history data from Excel files
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
from typing import Optional

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import Base
# Import models from the main models file
from app.models import Customer, Order, OrderStatus, GasProduct

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataImporter:
    """Import Excel data into the database"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize the importer with database connection"""
        # Use provided URL or get from settings
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # File paths
        self.base_path = "/Users/lgee258/Desktop/LuckyGas-v3/raw"
        self.client_file = os.path.join(self.base_path, "2025-05 commercial client list.xlsx")
        self.delivery_file = os.path.join(self.base_path, "2025-05 commercial deliver history.xlsx")
        
        # Product mapping
        self.product_mapping = {
            '50kg': {'id': 1, 'name': '50公斤瓦斯桶', 'size': 50.0, 'unit_price': 2500.0},
            '20kg': {'id': 2, 'name': '20公斤瓦斯桶', 'size': 20.0, 'unit_price': 1200.0},
            '16kg': {'id': 3, 'name': '16公斤瓦斯桶', 'size': 16.0, 'unit_price': 1000.0},
            '10kg': {'id': 4, 'name': '10公斤瓦斯桶', 'size': 10.0, 'unit_price': 700.0},
            '4kg': {'id': 5, 'name': '4公斤瓦斯桶', 'size': 4.0, 'unit_price': 350.0},
        }
        
    def clean_numeric(self, value):
        """Clean numeric values"""
        if pd.isna(value):
            return 0
        try:
            return int(float(str(value).replace(',', '')))
        except:
            return 0
    
    def clean_string(self, value):
        """Clean string values"""
        if pd.isna(value):
            return None
        return str(value).strip()
    
    def import_products(self):
        """Import gas products into the database"""
        logger.info("Importing gas products...")
        
        for key, product_data in self.product_mapping.items():
            # Check if product exists
            existing = self.session.query(GasProduct).filter_by(id=product_data['id']).first()
            if not existing:
                product = GasProduct(
                    id=product_data['id'],
                    name=product_data['name'],
                    size=product_data['size'],
                    unit_price=product_data['unit_price'],
                    is_active=True
                )
                self.session.add(product)
                logger.info(f"Added product: {product_data['name']}")
        
        self.session.commit()
        logger.info("Products imported successfully")
    
    def import_customers(self):
        """Import customer data from Excel"""
        logger.info(f"Reading customer data from: {self.client_file}")
        
        # Read Excel file
        df = pd.read_excel(self.client_file)
        logger.info(f"Found {len(df)} customers in Excel file")
        
        # Column mapping (adjust based on actual Excel columns)
        column_mapping = {
            '客戶代號': 'customer_code',
            '發票抬頭': 'invoice_title',
            '客戶簡稱': 'short_name',
            '送貨地址': 'address',
            '營業區域': 'area',
            '50KG': 'cylinders_50kg',
            '20KG': 'cylinders_20kg',
            '16KG': 'cylinders_16kg',
            '10KG': 'cylinders_10kg',
            '4KG': 'cylinders_4kg',
            '計價方式': 'pricing_method',
            '收款方式': 'payment_method',
            '設備客戶買斷': 'is_equipment_purchased',
            '已解約': 'is_terminated',
        }
        
        imported_count = 0
        updated_count = 0
        
        for index, row in df.iterrows():
            try:
                # Get customer code
                customer_code = self.clean_string(row.get('客戶代號'))
                if not customer_code:
                    logger.warning(f"Row {index}: Missing customer code, skipping")
                    continue
                
                # Check if customer exists
                existing_customer = self.session.query(Customer).filter_by(
                    customer_code=customer_code
                ).first()
                
                if existing_customer:
                    # Update existing customer
                    for excel_col, db_col in column_mapping.items():
                        if excel_col in row:
                            value = row[excel_col]
                            if db_col.startswith('cylinders_'):
                                value = self.clean_numeric(value)
                            elif db_col in ['is_equipment_purchased', 'is_terminated']:
                                value = bool(value) if not pd.isna(value) else False
                            else:
                                value = self.clean_string(value)
                            
                            if value is not None:
                                setattr(existing_customer, db_col, value)
                    
                    updated_count += 1
                    logger.debug(f"Updated customer: {customer_code}")
                else:
                    # Create new customer
                    customer_data = {
                        'customer_code': customer_code,
                        'invoice_title': self.clean_string(row.get('發票抬頭')),
                        'short_name': self.clean_string(row.get('客戶簡稱')) or customer_code,
                        'address': self.clean_string(row.get('送貨地址')) or '待補充',
                        'area': self.clean_string(row.get('營業區域')),
                        'cylinders_50kg': self.clean_numeric(row.get('50KG')),
                        'cylinders_20kg': self.clean_numeric(row.get('20KG')),
                        'cylinders_16kg': self.clean_numeric(row.get('16KG')),
                        'cylinders_10kg': self.clean_numeric(row.get('10KG')),
                        'cylinders_4kg': self.clean_numeric(row.get('4KG')),
                        'pricing_method': self.clean_string(row.get('計價方式')),
                        'payment_method': self.clean_string(row.get('收款方式')),
                        'is_equipment_purchased': bool(row.get('設備客戶買斷')) if not pd.isna(row.get('設備客戶買斷')) else False,
                        'is_terminated': bool(row.get('已解約')) if not pd.isna(row.get('已解約')) else False,
                        'customer_type': 'commercial',  # All are commercial from this file
                        'is_active': True,
                    }
                    
                    new_customer = Customer(**customer_data)
                    self.session.add(new_customer)
                    imported_count += 1
                    logger.debug(f"Added new customer: {customer_code}")
                
            except Exception as e:
                logger.error(f"Error processing row {index}: {str(e)}")
                continue
        
        # Commit changes
        try:
            self.session.commit()
            logger.info(f"Customer import completed: {imported_count} new, {updated_count} updated")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to commit customer data: {str(e)}")
            raise
    
    def import_delivery_history(self):
        """Import delivery history from Excel"""
        logger.info(f"Reading delivery history from: {self.delivery_file}")
        
        # Read Excel file
        df = pd.read_excel(self.delivery_file)
        logger.info(f"Found {len(df)} delivery records in Excel file")
        
        # Group by date and customer to create delivery batches
        imported_count = 0
        
        for index, row in df.iterrows():
            try:
                # Parse date
                transaction_date = pd.to_datetime(row.get('交易日期'))
                if pd.isna(transaction_date):
                    logger.warning(f"Row {index}: Missing transaction date, skipping")
                    continue
                
                # Get customer
                customer_code = self.clean_string(row.get('客戶代號'))
                if not customer_code:
                    logger.warning(f"Row {index}: Missing customer code, skipping")
                    continue
                
                customer = self.session.query(Customer).filter_by(
                    customer_code=customer_code
                ).first()
                
                if not customer:
                    logger.warning(f"Row {index}: Customer {customer_code} not found, skipping")
                    continue
                
                # Create delivery history record
                delivery_history = DeliveryHistory(
                    customer_id=customer.id,
                    delivery_date=transaction_date.date(),
                    delivery_time=self.clean_string(row.get('交易時間')),
                    total_amount=0,  # Will calculate from items
                    delivery_address=customer.address,
                    driver_id=None,  # Would need driver mapping
                    route_id=None,  # Would need route mapping
                    status='completed',
                    notes=self.clean_string(row.get('備註'))
                )
                self.session.add(delivery_history)
                self.session.flush()  # Get the ID
                
                # Add delivery items
                total_amount = 0
                cylinders = {
                    '50kg': self.clean_numeric(row.get('50KG')),
                    '20kg': self.clean_numeric(row.get('20KG')),
                    '16kg': self.clean_numeric(row.get('16KG')),
                    '10kg': self.clean_numeric(row.get('10KG')),
                    '4kg': self.clean_numeric(row.get('4KG')),
                }
                
                for product_key, quantity in cylinders.items():
                    if quantity > 0:
                        product_info = self.product_mapping[product_key]
                        
                        item = DeliveryHistoryItem(
                            delivery_history_id=delivery_history.id,
                            product_id=product_info['id'],
                            quantity=quantity,
                            unit_price=product_info['unit_price'],
                            subtotal=quantity * product_info['unit_price']
                        )
                        self.session.add(item)
                        total_amount += item.subtotal
                
                # Update total amount
                delivery_history.total_amount = total_amount
                
                # Also create an Order record for tracking
                order = Order(
                    customer_id=customer.id,
                    order_date=transaction_date.date(),
                    delivery_date=transaction_date.date(),
                    status=OrderStatus.COMPLETED,
                    total_amount=total_amount,
                    delivery_address=customer.address,
                    notes=f"Imported from May 2025 history"
                )
                self.session.add(order)
                self.session.flush()
                
                # Add order items
                for product_key, quantity in cylinders.items():
                    if quantity > 0:
                        product_info = self.product_mapping[product_key]
                        
                        order_item = OrderItem(
                            order_id=order.id,
                            product_id=product_info['id'],
                            quantity=quantity,
                            unit_price=product_info['unit_price'],
                            subtotal=quantity * product_info['unit_price']
                        )
                        self.session.add(order_item)
                
                imported_count += 1
                
                if imported_count % 100 == 0:
                    logger.info(f"Processed {imported_count} delivery records...")
                    self.session.commit()
                
            except Exception as e:
                logger.error(f"Error processing row {index}: {str(e)}")
                self.session.rollback()
                continue
        
        # Final commit
        try:
            self.session.commit()
            logger.info(f"Delivery history import completed: {imported_count} records imported")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to commit delivery history: {str(e)}")
            raise
    
    def generate_statistics(self):
        """Generate statistics from imported data"""
        logger.info("Generating statistics...")
        
        # Customer statistics
        total_customers = self.session.query(Customer).count()
        active_customers = self.session.query(Customer).filter_by(is_terminated=False).count()
        commercial_customers = self.session.query(Customer).filter_by(customer_type='commercial').count()
        
        # Order statistics
        total_orders = self.session.query(Order).count()
        completed_orders = self.session.query(Order).filter_by(status=OrderStatus.COMPLETED).count()
        
        # Delivery statistics
        total_deliveries = self.session.query(DeliveryHistory).count()
        
        logger.info("=" * 60)
        logger.info("IMPORT STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total Customers: {total_customers}")
        logger.info(f"Active Customers: {active_customers}")
        logger.info(f"Commercial Customers: {commercial_customers}")
        logger.info(f"Total Orders: {total_orders}")
        logger.info(f"Completed Orders: {completed_orders}")
        logger.info(f"Total Deliveries: {total_deliveries}")
        logger.info("=" * 60)
    
    def run(self):
        """Run the complete import process"""
        logger.info("Starting Lucky Gas May 2025 data import...")
        logger.info("=" * 60)
        
        try:
            # Import products first
            self.import_products()
            
            # Import customers
            self.import_customers()
            
            # Import delivery history
            self.import_delivery_history()
            
            # Generate statistics
            self.generate_statistics()
            
            logger.info("Data import completed successfully!")
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
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
        logger.error(f"Client file not found: {client_file}")
        return
    
    if not os.path.exists(delivery_file):
        logger.error(f"Delivery file not found: {delivery_file}")
        return
    
    # Run import
    importer = DataImporter()
    importer.run()

if __name__ == "__main__":
    main()