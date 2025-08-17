"""
Fix database schema - add missing columns
"""
import psycopg2
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas")

def fix_schema():
    """Add missing columns to existing tables"""
    conn = None
    cursor = None
    
    try:
        # Connect to database
        logger.info(f"Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Add missing columns if they don't exist
        alter_statements = [
            # Add is_active to customers if missing
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='customers' AND column_name='is_active') THEN
                    ALTER TABLE customers ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
                END IF;
            END $$;
            """,
            
            # Add delivery_date to orders if missing
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='delivery_date') THEN
                    ALTER TABLE orders ADD COLUMN delivery_date TIMESTAMP WITH TIME ZONE;
                END IF;
            END $$;
            """,
            
            # Add updated_at to customers if missing
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='customers' AND column_name='updated_at') THEN
                    ALTER TABLE customers ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE;
                END IF;
            END $$;
            """,
            
            # Add created_at to customers if missing
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='customers' AND column_name='created_at') THEN
                    ALTER TABLE customers ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
                END IF;
            END $$;
            """,
            
            # Add total_amount to orders if missing
            """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='total_amount') THEN
                    ALTER TABLE orders ADD COLUMN total_amount NUMERIC(10,2) DEFAULT 0;
                END IF;
            END $$;
            """,
        ]
        
        for statement in alter_statements:
            try:
                cursor.execute(statement)
                logger.info(f"✅ Executed: {statement[:50]}...")
            except Exception as e:
                logger.warning(f"Statement might have failed (column may already exist): {e}")
        
        # Commit changes
        conn.commit()
        logger.info("✅ Schema fixes applied successfully!")
        
        # List current columns
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'customers' 
            ORDER BY ordinal_position
        """)
        
        logger.info("\nCurrent customers table columns:")
        for col in cursor.fetchall():
            logger.info(f"  - {col[0]}: {col[1]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to fix schema: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    if fix_schema():
        logger.info("\n✅ Database schema is ready for import!")
    else:
        logger.error("\n❌ Failed to fix database schema")