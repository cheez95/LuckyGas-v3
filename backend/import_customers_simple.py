#!/usr/bin/env python3
"""Simple script to import customers from Excel file to database."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Customer
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_customers():
    """Import customers from Excel file."""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    
    # Read Excel file
    excel_file = "../raw/2025-05 commercial client list.xlsx"
    if not os.path.exists(excel_file):
        logger.error(f"Excel file not found: {excel_file}")
        return
    
    logger.info(f"Reading Excel file: {excel_file}")
    df = pd.read_excel(excel_file, sheet_name='客戶資料')
    
    logger.info(f"Found {len(df)} customers in Excel file")
    
    # Import customers
    with Session(engine) as session:
        # Check if customers already exist
        existing_count = session.query(Customer).count()
        if existing_count > 0:
            logger.info(f"Database already has {existing_count} customers. Skipping import.")
            return
        
        imported = 0
        for index, row in df.iterrows():
            try:
                customer = Customer(
                    customer_code=str(row.get('客戶', f'CUST-{index+1}')),
                    full_name=str(row.get('電子發票抬頭', row.get('客戶', f'Customer {index+1}'))),
                    short_name=str(row.get('客戶簡稱', row.get('客戶', f'Customer {index+1}'))),
                    address=str(row.get('地址', 'No Address')),
                    area='',  # Will be extracted from address later
                    customer_type='commercial',
                    is_terminated=bool(row.get('已解約', False)),
                    cylinders_50kg=int(row.get('50KG', 0) or 0),
                    cylinders_20kg=int(row.get('20KG', 0) or 0),
                    cylinders_16kg=int(row.get('16KG', 0) or 0),
                    cylinders_10kg=int(row.get('10KG', 0) or 0),
                    cylinders_4kg=int(row.get('4KG', 0) or 0),
                )
                session.add(customer)
                imported += 1
                
                if imported % 100 == 0:
                    session.commit()
                    logger.info(f"Imported {imported} customers...")
                    
            except Exception as e:
                logger.error(f"Error importing customer at row {index}: {e}")
                continue
        
        session.commit()
        logger.info(f"Successfully imported {imported} customers")

if __name__ == "__main__":
    import_customers()