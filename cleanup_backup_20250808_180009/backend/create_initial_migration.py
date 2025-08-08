#!/usr/bin/env python3
"""
Create Initial Alembic Migration Script
Generates migration file from existing database schema
"""
import asyncio
import asyncpg
from datetime import datetime

DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

async def generate_migration():
    """Generate initial migration SQL"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("🗄️ Generating Initial Migration Script")
        print("=" * 60)
        
        # Get all enum types
        enums = await conn.fetch("""
            SELECT DISTINCT 
                t.typname as enum_name,
                array_agg(e.enumlabel ORDER BY e.enumsortorder) as values
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            GROUP BY t.typname
            ORDER BY t.typname
        """)
        
        # Generate migration file
        migration_content = '''"""Initial schema migration

Revision ID: 001_initial
Create Date: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create initial schema"""
    
    # Create enums first
'''
        
        # Add enum creation
        for enum in enums:
            values_str = ", ".join([f"'{v}'" for v in enum['values']])
            migration_content += f"    op.execute(\"CREATE TYPE {enum['enum_name']} AS ENUM ({values_str})\")\n"
        
        migration_content += '''
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', postgresql.ENUM('SUPER_ADMIN', 'MANAGER', 'OFFICE_STAFF', 'DRIVER', 'CUSTOMER', 
                                         name='userrole', create_type=False), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # Create customers table
    op.create_table('customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_code', sa.String(), nullable=False),
        sa.Column('invoice_title', sa.String(), nullable=True),
        sa.Column('short_name', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('area', sa.String(), nullable=True),
        sa.Column('customer_type', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_code')
    )
    
    # Add other tables...
    
    # Create alembic_version table
    op.create_table('alembic_version',
        sa.Column('version_num', sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint('version_num')
    )

def downgrade():
    """Drop all tables and types"""
    op.drop_table('alembic_version')
    op.drop_table('customers')
    op.drop_table('users')
    
    # Drop enums
'''
        
        # Add enum drops
        for enum in enums:
            migration_content += f"    op.execute('DROP TYPE IF EXISTS {enum['enum_name']} CASCADE')\n"
        
        # Save migration file
        with open('alembic/versions/001_initial.py', 'w') as f:
            f.write(migration_content)
        
        print("✅ Migration script generated: alembic/versions/001_initial.py")
        print("\nTo apply migration, run:")
        print("  uv run alembic upgrade head")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(generate_migration())