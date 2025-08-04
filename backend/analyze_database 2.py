#!/usr/bin/env python3
"""
Database Schema Analysis Script
Analyzes the current database state and generates documentation
"""
import asyncio
import asyncpg
import json
from datetime import datetime
from typing import Dict, List, Any

DATABASE_URL = "postgresql://luckygas:staging-password-2025@35.194.143.37/luckygas"

async def analyze_database():
    """Analyze database schema and generate report"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("🗄️ Lucky Gas Database Schema Analysis")
        print("=" * 60)
        print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database: luckygas @ 35.194.143.37")
        print("=" * 60)
        
        # 1. Get all tables
        tables = await conn.fetch("""
            SELECT 
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_schema = 'public' AND table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        print(f"\n📊 Total Tables: {len(tables)}")
        print("-" * 40)
        for table in tables:
            # Get row count
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table['table_name']}")
            print(f"  • {table['table_name']}: {count:,} rows, {table['column_count']} columns")
        
        # 2. Get all enum types
        enums = await conn.fetch("""
            SELECT 
                t.typname as enum_name,
                array_agg(e.enumlabel ORDER BY e.enumsortorder) as values
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            GROUP BY t.typname
            ORDER BY t.typname;
        """)
        
        print(f"\n🏷️ Enum Types: {len(enums)}")
        print("-" * 40)
        for enum in enums:
            print(f"  • {enum['enum_name']}: {', '.join(enum['values'])}")
        
        # 3. Check for constraints
        constraints = await conn.fetch("""
            SELECT 
                conname as constraint_name,
                contype as constraint_type,
                conrelid::regclass as table_name,
                confrelid::regclass as foreign_table
            FROM pg_constraint
            WHERE connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND contype IN ('f', 'u', 'c')
            ORDER BY conrelid::regclass::text, conname;
        """)
        
        print(f"\n🔗 Constraints: {len(constraints)}")
        print("-" * 40)
        fk_count = sum(1 for c in constraints if c['constraint_type'] == 'f')
        unique_count = sum(1 for c in constraints if c['constraint_type'] == 'u')
        check_count = sum(1 for c in constraints if c['constraint_type'] == 'c')
        print(f"  • Foreign Keys: {fk_count}")
        print(f"  • Unique Constraints: {unique_count}")
        print(f"  • Check Constraints: {check_count}")
        
        # 4. Check indexes
        indexes = await conn.fetch("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """)
        
        print(f"\n📍 Indexes: {len(indexes)}")
        
        # 5. Check for migration issues
        print("\n⚠️ Potential Issues:")
        print("-" * 40)
        
        # Check alembic version
        try:
            alembic_version = await conn.fetchval("""
                SELECT version_num FROM alembic_version LIMIT 1;
            """)
            print(f"  • Current Alembic Version: {alembic_version or 'Not found'}")
        except asyncpg.exceptions.UndefinedTableError:
            print("  • ⚠️ Alembic version table not found - migrations not run yet")
        
        # Check for orphaned constraints
        orphaned = await conn.fetch("""
            SELECT conname 
            FROM pg_constraint 
            WHERE NOT EXISTS (
                SELECT 1 FROM pg_class WHERE oid = conrelid
            );
        """)
        if orphaned:
            print(f"  • ⚠️ Found {len(orphaned)} orphaned constraints!")
        else:
            print("  • ✅ No orphaned constraints found")
        
        # Generate detailed schema for key tables
        key_tables = ['users', 'customers', 'orders', 'routes', 'drivers']
        
        print("\n📋 Key Table Schemas:")
        print("=" * 60)
        
        for table_name in key_tables:
            # Check if table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = $1
                )
            """, table_name)
            
            if not exists:
                print(f"\n❌ Table '{table_name}' does not exist!")
                continue
            
            columns = await conn.fetch("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position;
            """, table_name)
            
            print(f"\n📋 Table: {table_name}")
            print("-" * 50)
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                length = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
                print(f"  {col['column_name']}: {col['data_type']}{length} {nullable}{default}")
        
        # Generate SQL for cleanup
        print("\n🧹 Cleanup SQL Commands:")
        print("=" * 60)
        print("-- Drop all foreign key constraints")
        print("DO $$ DECLARE r RECORD;")
        print("BEGIN")
        print("  FOR r IN (SELECT conname, conrelid::regclass FROM pg_constraint WHERE contype = 'f')")
        print("  LOOP")
        print("    EXECUTE 'ALTER TABLE ' || r.conrelid || ' DROP CONSTRAINT ' || r.conname;")
        print("  END LOOP;")
        print("END $$;")
        
        # Save report
        report = {
            "analysis_date": datetime.now().isoformat(),
            "database": "luckygas",
            "tables_count": len(tables),
            "enums_count": len(enums),
            "constraints_count": len(constraints),
            "indexes_count": len(indexes),
            "alembic_version": alembic_version,
            "tables": [dict(t) for t in tables],
            "enums": [dict(e) for e in enums]
        }
        
        with open("database_analysis_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print("\n✅ Analysis complete! Report saved to database_analysis_report.json")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(analyze_database())