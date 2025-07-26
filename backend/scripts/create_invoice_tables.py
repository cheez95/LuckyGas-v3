#!/usr/bin/env python3
"""
Create invoice, payment, and credit note tables for Sprint 5
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

from app.models import Invoice, InvoiceItem, Payment, CreditNote
from app.core.database import Base


async def create_invoice_tables():
    """Create all invoice-related tables"""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://luckygas:luckygas123@localhost:5433/luckygas"
    )
    
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        # Create tables using Base.metadata
        print("🔨 Creating invoice tables...")
        
        # Check if tables already exist
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('invoices', 'invoice_items', 'payments', 'credit_notes')
        """))
        existing_tables = [row[0] for row in result]
        
        if 'invoices' in existing_tables:
            print("ℹ️  Invoice tables already exist, skipping...")
        else:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Invoice tables created successfully!")
            
            # Add indexes that may not be in the model
            print("Adding additional indexes...")
            
            # Index for invoice number pattern search
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_invoice_number_pattern ON invoices(invoice_track, invoice_no)"
            ))
            
            # Index for payment tracking
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_payment_verification ON payments(is_verified, payment_date)"
            ))
            
            print("✅ Additional indexes created!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_invoice_tables())