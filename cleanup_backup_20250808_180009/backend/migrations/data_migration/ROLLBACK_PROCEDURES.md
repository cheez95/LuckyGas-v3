# Migration Rollback Procedures

## Overview

This document provides comprehensive procedures for managing rollbacks in the Lucky Gas data migration system. The rollback functionality ensures data integrity and provides recovery options in case of migration failures.

## Rollback Components

### 1. RollbackManager
The core component that handles all rollback operations:
- Creates backup points before migrations
- Manages rollback execution
- Maintains audit trails
- Verifies rollback success

### 2. MigrationTransaction
A context manager that provides automatic rollback on failure:
- Wraps migration operations in a transaction
- Automatically creates rollback points
- Triggers rollback on exceptions

### 3. MigrationBackup
Handles backup creation and restoration:
- Creates JSON backups of table data
- Verifies backup integrity with checksums
- Restores data from backup files

## Rollback Types

### 1. Full Rollback (Default)
- Restores the entire table to its pre-migration state
- Uses backup files for complete restoration
- Suitable for complete migration failures

### 2. Partial Rollback
- Removes only records added during the migration
- Preserves existing data
- Useful for partially successful migrations

### 3. Transaction Rollback
- Database-level transaction rollback
- Only available during active migrations
- Fastest rollback method

### 4. Backup Restore
- Direct restoration from backup files
- Can be used independently of migration context

## Usage Guide

### Using Rollback in Migration Script

#### 1. Running Migration with Rollback Support (Default)
```bash
# Dry run with rollback support
python migrations/data_migration/001_migrate_clients.py

# Production run with automatic rollback on failure
python migrations/data_migration/001_migrate_clients.py --production
```

#### 2. Disabling Rollback (Not Recommended)
```bash
python migrations/data_migration/001_migrate_clients.py --production --no-rollback
```

#### 3. Manual Rollback Execution
```bash
# Rollback using the latest rollback point
python migrations/data_migration/001_migrate_clients.py --rollback

# Rollback using specific rollback ID
python migrations/data_migration/001_migrate_clients.py --rollback rb_client_migration_20240120_143022
```

### Using the Rollback CLI

#### 1. List Available Rollback Points
```bash
python migrations/data_migration/rollback_cli.py list
```

Output:
```
Available Rollback Points:
+----------------------+----------------------+-----------+-----------+---------------------+--------------------------------+
| Rollback ID          | Migration ID         | Table     | Status    | Created At          | Description                    |
+======================+======================+===========+===========+=====================+================================+
| rb_client_migrat...  | client_migration_... | customers | completed | 2024-01-20 14:30:22 | Commercial client migration... |
+----------------------+----------------------+-----------+-----------+---------------------+--------------------------------+
```

#### 2. Execute a Rollback
```bash
# Full rollback (default)
python migrations/data_migration/rollback_cli.py execute rb_client_migration_20240120_143022

# Partial rollback
python migrations/data_migration/rollback_cli.py execute rb_client_migration_20240120_143022 --type partial
```

#### 3. View Rollback Details
```bash
python migrations/data_migration/rollback_cli.py details rb_client_migration_20240120_143022
```

#### 4. View Audit Log
```bash
python migrations/data_migration/rollback_cli.py audit --limit 50
```

#### 5. Create Manual Backup
```bash
python migrations/data_migration/rollback_cli.py backup customers --description "Pre-deployment backup"
```

### Using Rollback in Code

#### 1. Basic Usage with MigrationTransaction
```python
from rollback_manager import RollbackManager, MigrationTransaction

rollback_manager = RollbackManager(DATABASE_URL)

async with MigrationTransaction(
    rollback_manager,
    migration_id="my_migration_001",
    table_name="customers",
    description="Customer data import"
) as session:
    # Perform migration operations
    # Automatic rollback on any exception
    pass
```

#### 2. Manual Rollback Control
```python
# Create rollback point
rollback_id = await rollback_manager.create_rollback_point(
    session, "migration_001", "customers", "Test migration"
)

try:
    # Perform migration
    pass
except Exception as e:
    # Execute rollback
    await rollback_manager.execute_rollback(rollback_id, RollbackType.FULL)
    
# Verify rollback
verification = await rollback_manager.verify_rollback(rollback_id)
```

## Rollback Decision Matrix

| Scenario | Rollback Type | When to Use |
|----------|---------------|-------------|
| Complete migration failure | Full | Migration fails to start or crashes early |
| High failure rate (>10%) | Full | Too many records fail validation |
| Partial success with identifiable failures | Partial | Some records succeed, failed ones are tracked |
| Active transaction error | Transaction | Error during active database transaction |
| Data corruption detected | Backup Restore | Need to restore to known good state |

## Best Practices

### 1. Pre-Migration
- Always run migrations in dry-run mode first
- Verify backup creation before starting production migration
- Check available disk space for backup files
- Review existing data for conflicts

### 2. During Migration
- Monitor failure rates in real-time
- Set appropriate failure thresholds (default: 10%)
- Keep transaction sizes manageable (batch by 100 records)
- Log all errors with context

### 3. Post-Migration
- Verify migration success with row counts
- Check data integrity with spot checks
- Save audit logs for compliance
- Clean up old backup files after verification

### 4. Rollback Execution
- Always verify the rollback point before execution
- Confirm the action when using CLI
- Monitor rollback progress
- Verify data state after rollback

## Troubleshooting

### Common Issues

#### 1. Rollback Point Not Found
```
Error: Rollback point rb_xxx not found
```
**Solution**: List available rollback points with `rollback_cli.py list`

#### 2. Backup File Missing
```
Error: Backup file not found at path
```
**Solution**: Check backup directory permissions and disk space

#### 3. Checksum Verification Failed
```
Error: Backup checksum verification failed
```
**Solution**: Backup file may be corrupted. Use an earlier backup.

#### 4. Insufficient Permissions
```
Error: Permission denied for table truncation
```
**Solution**: Ensure database user has necessary permissions

### Recovery Procedures

#### From Complete Migration Failure
1. Identify the migration ID from logs
2. List rollback points: `rollback_cli.py list`
3. Execute full rollback: `rollback_cli.py execute <rollback_id>`
4. Verify data state
5. Fix issues and retry migration

#### From Partial Migration Failure
1. Review failure logs and statistics
2. Decide on partial vs full rollback
3. Execute appropriate rollback
4. Re-run migration for failed records only

#### From Corrupted State
1. Create manual backup of current state
2. Identify last known good backup
3. Execute backup restore
4. Verify data integrity
5. Document data loss if any

## Audit Trail

All rollback operations are logged with:
- Timestamp
- Event type (creation, execution, verification)
- User/process information
- Operation details
- Success/failure status

Audit logs are saved to: `migrations/rollback_audit.json`

## Testing Rollback Procedures

Run the test suite to verify rollback functionality:
```bash
python migrations/data_migration/test_rollback.py
```

Tests include:
- Backup creation and restoration
- Partial rollback scenarios
- Transaction rollback
- Audit trail generation

## Security Considerations

1. **Backup File Security**
   - Backup files contain sensitive data
   - Store in secure location with restricted access
   - Encrypt backups for production data

2. **Access Control**
   - Limit rollback execution to authorized personnel
   - Log all rollback attempts
   - Require confirmation for production rollbacks

3. **Data Retention**
   - Define backup retention policies
   - Clean up old backups regularly
   - Maintain audit logs for compliance period

## Emergency Contacts

For critical rollback situations:
- Database Admin: [Contact Info]
- DevOps Lead: [Contact Info]
- Data Team Lead: [Contact Info]

## Appendix: Quick Reference

### Commands
```bash
# List rollbacks
rollback_cli.py list

# Execute rollback
rollback_cli.py execute <id> [--type full|partial|backup|transaction]

# View details
rollback_cli.py details <id>

# View audit log
rollback_cli.py audit [--limit N]

# Create backup
rollback_cli.py backup <table> [--description "text"]
```

### Migration Flags
```bash
--production         # Run in production mode
--no-rollback       # Disable rollback support
--rollback <id>     # Execute rollback instead of migration
```

### Python API
```python
# Create rollback point
rollback_id = await rollback_manager.create_rollback_point(session, migration_id, table, description)

# Execute rollback
result = await rollback_manager.execute_rollback(rollback_id, rollback_type)

# Verify rollback
verification = await rollback_manager.verify_rollback(rollback_id)

# Get history
history = rollback_manager.get_rollback_history()
```