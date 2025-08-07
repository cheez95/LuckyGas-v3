# Lucky Gas Data Migration Guide

## Overview

This directory contains scripts for migrating historical data from Excel files to the PostgreSQL database. The migration process is designed to be safe, resumable, and efficient.

## Migration Scripts

### 1. Customer Data Analysis (`001_analyze_client_data.py`)
- **Author**: Sam (QA Specialist)
- **Purpose**: Analyzes the client Excel file to understand data structure
- **Output**: `client_data_analysis.json` with detailed analysis

### 2. Customer Migration (`002_fix_column_mapping.py`)
- **Author**: Sam (QA Specialist)
- **Purpose**: Migrates commercial clients from Excel to PostgreSQL
- **Features**:
  - Corrected column mapping
  - Validation and error handling
  - Dry run mode for testing
  - Duplicate detection

### 3. Delivery History Analysis (`analyze_delivery_data.py`)
- **Author**: Devin (Data Migration Specialist)
- **Purpose**: Analyzes delivery history Excel file
- **Key Findings**:
  - 349,920 records to migrate
  - Taiwan date format (民國年) used
  - Multiple cylinder types and flow meter data

### 4. Delivery History Migration (`003_migrate_deliveries.py`)
- **Author**: Devin (Data Migration Specialist)
- **Purpose**: Migrates delivery history with advanced features
- **Features**:
  - Batch processing (5,000 records per batch)
  - Taiwan date conversion
  - Checkpoint recovery for resumability
  - Memory-efficient chunked reading
  - Progress tracking with ETA
  - Missing customer tracking

### 5. Test Scripts
- `test_delivery_migration.py`: Tests delivery migration logic

## Migration Order

**IMPORTANT**: Run migrations in this exact order:

1. **Analyze customer data**: `python 001_analyze_client_data.py`
2. **Migrate customers**: `python 002_fix_column_mapping.py --production`
3. **Analyze delivery data**: `python analyze_delivery_data.py`
4. **Migrate deliveries**: `python 003_migrate_deliveries.py --production`

## Prerequisites

1. **Database Setup**:
   ```bash
   # Ensure PostgreSQL is running
   # Database tables should be created via Alembic migrations
   cd backend
   alembic upgrade head
   ```

2. **Environment Variables**:
   ```bash
   # Set in backend/.env
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost/luckygas
   ```

3. **Excel Files**:
   - Place Excel files in `raw/` directory
   - Required files:
     - `2025-05 commercial client list.xlsx`
     - `2025-05 commercial deliver history.xlsx`

## Usage Examples

### Dry Run (Test Mode)
```bash
# Test customer migration
python 002_fix_column_mapping.py

# Test delivery migration
python 003_migrate_deliveries.py
```

### Production Run
```bash
# Migrate customers (required first!)
python 002_fix_column_mapping.py --production

# Migrate delivery history
python 003_migrate_deliveries.py --production
```

### Custom File Path
```bash
# Use different Excel file
python 003_migrate_deliveries.py --file "path/to/delivery.xlsx" --production
```

## Features

### Checkpoint Recovery
The delivery migration supports checkpoint recovery. If interrupted:
- Progress is saved to `delivery_migration_checkpoint.json`
- Re-run the same command to resume from last checkpoint
- Checkpoint is automatically deleted on successful completion

### Batch Processing
- Processes 5,000 records per batch
- Commits after each batch for data safety
- Shows progress and ETA during migration

### Error Handling
- Comprehensive error logging
- Missing customer tracking
- Invalid date handling
- Data quality validation

## Monitoring Progress

During migration, you'll see:
```
🔄 Processing batch 15 (5000 records)...
  ✅ Batch 15 completed in 12.3s (406 records/sec)
  📊 Progress: 35.7% (75,000/349,920)
  ⏱️  Estimated time remaining: 0:11:17
```

## Troubleshooting

### Common Issues

1. **Missing Customers**:
   - Ensure customer migration completed successfully
   - Check customer codes match between files
   - Review missing customer report at end

2. **Memory Issues**:
   - Batch size is optimized for 8GB RAM
   - Monitor system memory during migration
   - Reduce batch size if needed

3. **Date Conversion Errors**:
   - Script handles Taiwan dates (民國年)
   - Check for unusual date formats in Excel
   - Invalid dates are logged and skipped

### Recovery from Errors

If migration fails:
1. Check the error logs
2. Fix the underlying issue
3. Re-run the migration (it will resume from checkpoint)
4. No need to delete already migrated data

## Performance

Expected performance:
- Customer migration: ~1,000 records/minute
- Delivery migration: ~20,000-30,000 records/minute
- Total time for 350K deliveries: ~15-20 minutes

## Post-Migration Verification

After migration:
```sql
-- Check customer count
SELECT COUNT(*) FROM customers;

-- Check delivery count
SELECT COUNT(*) FROM delivery_history;

-- Verify date conversion
SELECT MIN(transaction_date), MAX(transaction_date) 
FROM delivery_history;

-- Check data quality
SELECT COUNT(*) FROM delivery_history 
WHERE customer_id IS NULL;
```

## Data Quality Notes

1. **Customer Codes**: Must be 7 digits, stored as strings
2. **Taiwan Dates**: Converted from 民國 (1130520) to Western (2024-05-20)
3. **Cylinder Quantities**: Default to 0 if missing
4. **Flow Meter Data**: Stored as floats, default to 0.0

## Support

For issues or questions:
1. Check error logs in console output
2. Review checkpoint file for detailed error info
3. Verify Excel file format matches expected structure
4. Contact the BMad team:
   - Sam (QA): Customer data issues
   - Devin (Data Migration): Delivery history issues