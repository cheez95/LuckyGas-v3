#!/usr/bin/env python3
"""
Migration Rollback Manager
Provides comprehensive rollback capabilities for data migrations
Author: Devin (Data Migration Specialist)
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import aiofiles
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RollbackType(Enum):
    """Types of rollback operations"""
    TRANSACTION = "transaction"
    BACKUP_RESTORE = "backup_restore"
    PARTIAL = "partial"
    FULL = "full"


class RollbackStatus(Enum):
    """Status of rollback operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


class MigrationBackup:
    """Handles backup creation and restoration for migrations"""
    
    def __init__(self, backup_dir: str = "migrations/backups"):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
        
    async def create_backup(self, session: AsyncSession, table_name: str, 
                          migration_id: str) -> Dict[str, Any]:
        """Create a backup of the current table state"""
        backup_info = {
            'migration_id': migration_id,
            'table_name': table_name,
            'timestamp': datetime.utcnow().isoformat(),
            'row_count': 0,
            'checksum': '',
            'file_path': ''
        }
        
        try:
            # Create backup filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(
                self.backup_dir, 
                f"{table_name}_{migration_id}_{timestamp}.json"
            )
            
            # Query all data from table
            result = await session.execute(
                text(f"SELECT * FROM {table_name} ORDER BY id")
            )
            rows = result.fetchall()
            
            # Convert rows to dict format
            data = []
            columns = result.keys()
            for row in rows:
                data.append(dict(zip(columns, row)))
            
            # Calculate checksum
            data_str = json.dumps(data, sort_keys=True, default=str)
            checksum = hashlib.sha256(data_str.encode()).hexdigest()
            
            # Write backup file
            async with aiofiles.open(backup_file, 'w') as f:
                await f.write(json.dumps({
                    'backup_info': backup_info,
                    'data': data
                }, default=str, indent=2))
            
            backup_info.update({
                'row_count': len(data),
                'checksum': checksum,
                'file_path': backup_file
            })
            
            logger.info(f"Created backup for {table_name}: {len(data)} rows, checksum: {checksum[:8]}...")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            raise
    
    async def restore_backup(self, session: AsyncSession, backup_file: str) -> Dict[str, Any]:
        """Restore data from a backup file"""
        try:
            # Read backup file
            async with aiofiles.open(backup_file, 'r') as f:
                backup_data = json.loads(await f.read())
            
            backup_info = backup_data['backup_info']
            data = backup_data['data']
            table_name = backup_info['table_name']
            
            # Verify checksum
            data_str = json.dumps(data, sort_keys=True, default=str)
            current_checksum = hashlib.sha256(data_str.encode()).hexdigest()
            
            if current_checksum != backup_info['checksum']:
                raise ValueError("Backup checksum verification failed")
            
            # Clear existing data
            await session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            
            # Restore data
            for row in data:
                columns = list(row.keys())
                values = list(row.values())
                placeholders = [f":p{i}" for i in range(len(values))]
                
                query = f"""
                    INSERT INTO {table_name} ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                """
                
                params = {f"p{i}": val for i, val in enumerate(values)}
                await session.execute(text(query), params)
            
            await session.commit()
            
            logger.info(f"Restored {len(data)} rows to {table_name}")
            return {
                'status': 'success',
                'rows_restored': len(data),
                'table_name': table_name
            }
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {str(e)}")
            await session.rollback()
            raise


class RollbackManager:
    """Manages rollback operations for migrations"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.backup_manager = MigrationBackup()
        self.audit_log = []
        self.rollback_points = {}
        
    async def create_rollback_point(self, session: AsyncSession, 
                                  migration_id: str, table_name: str,
                                  description: str) -> str:
        """Create a rollback point before migration"""
        rollback_id = f"rb_{migration_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Create backup
            backup_info = await self.backup_manager.create_backup(
                session, table_name, migration_id
            )
            
            # Store rollback point info
            self.rollback_points[rollback_id] = {
                'id': rollback_id,
                'migration_id': migration_id,
                'table_name': table_name,
                'description': description,
                'created_at': datetime.utcnow().isoformat(),
                'backup_info': backup_info,
                'status': RollbackStatus.PENDING.value
            }
            
            # Log audit entry
            self._log_audit_event(
                'rollback_point_created',
                rollback_id,
                {'description': description, 'table': table_name}
            )
            
            logger.info(f"Created rollback point: {rollback_id}")
            return rollback_id
            
        except Exception as e:
            logger.error(f"Failed to create rollback point: {str(e)}")
            raise
    
    async def execute_rollback(self, rollback_id: str, 
                             rollback_type: RollbackType = RollbackType.FULL) -> Dict[str, Any]:
        """Execute a rollback operation"""
        if rollback_id not in self.rollback_points:
            raise ValueError(f"Rollback point {rollback_id} not found")
        
        rollback_info = self.rollback_points[rollback_id]
        rollback_info['status'] = RollbackStatus.IN_PROGRESS.value
        
        engine = create_async_engine(self.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                result = await self._perform_rollback(
                    session, rollback_info, rollback_type
                )
                
                rollback_info['status'] = RollbackStatus.COMPLETED.value
                rollback_info['completed_at'] = datetime.utcnow().isoformat()
                
                # Log audit entry
                self._log_audit_event(
                    'rollback_executed',
                    rollback_id,
                    {'type': rollback_type.value, 'result': result}
                )
                
                return result
                
        except Exception as e:
            rollback_info['status'] = RollbackStatus.FAILED.value
            rollback_info['error'] = str(e)
            
            self._log_audit_event(
                'rollback_failed',
                rollback_id,
                {'error': str(e)}
            )
            
            logger.error(f"Rollback failed: {str(e)}")
            raise
        finally:
            await engine.dispose()
    
    async def _perform_rollback(self, session: AsyncSession, 
                              rollback_info: Dict, 
                              rollback_type: RollbackType) -> Dict[str, Any]:
        """Perform the actual rollback operation"""
        if rollback_type == RollbackType.BACKUP_RESTORE:
            # Restore from backup
            backup_file = rollback_info['backup_info']['file_path']
            return await self.backup_manager.restore_backup(session, backup_file)
            
        elif rollback_type == RollbackType.TRANSACTION:
            # Transaction-based rollback (for active transactions)
            await session.rollback()
            return {'status': 'success', 'type': 'transaction_rollback'}
            
        elif rollback_type == RollbackType.PARTIAL:
            # Partial rollback - restore specific records
            return await self._perform_partial_rollback(session, rollback_info)
            
        else:  # FULL rollback
            # Full restore from backup
            backup_file = rollback_info['backup_info']['file_path']
            return await self.backup_manager.restore_backup(session, backup_file)
    
    async def _perform_partial_rollback(self, session: AsyncSession, 
                                      rollback_info: Dict) -> Dict[str, Any]:
        """Perform partial rollback for failed records"""
        table_name = rollback_info['table_name']
        migration_id = rollback_info['migration_id']
        
        # Get records added by this migration
        result = await session.execute(
            text(f"""
                SELECT * FROM {table_name} 
                WHERE created_at >= :migration_start
                ORDER BY id
            """),
            {"migration_start": rollback_info['created_at']}
        )
        
        migrated_records = result.fetchall()
        
        # Delete migrated records
        if migrated_records:
            ids = [row[0] for row in migrated_records]  # Assuming first column is id
            await session.execute(
                text(f"DELETE FROM {table_name} WHERE id = ANY(:ids)"),
                {"ids": ids}
            )
            await session.commit()
        
        return {
            'status': 'success',
            'type': 'partial_rollback',
            'records_removed': len(migrated_records)
        }
    
    async def verify_rollback(self, rollback_id: str) -> Dict[str, Any]:
        """Verify that rollback was successful"""
        if rollback_id not in self.rollback_points:
            raise ValueError(f"Rollback point {rollback_id} not found")
        
        rollback_info = self.rollback_points[rollback_id]
        
        engine = create_async_engine(self.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                # Get current state
                table_name = rollback_info['table_name']
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                current_count = result.scalar()
                
                # Compare with backup
                expected_count = rollback_info['backup_info']['row_count']
                
                verification_result = {
                    'status': 'verified' if current_count == expected_count else 'mismatch',
                    'current_count': current_count,
                    'expected_count': expected_count,
                    'rollback_id': rollback_id
                }
                
                if verification_result['status'] == 'verified':
                    rollback_info['status'] = RollbackStatus.VERIFIED.value
                
                self._log_audit_event(
                    'rollback_verified',
                    rollback_id,
                    verification_result
                )
                
                return verification_result
                
        finally:
            await engine.dispose()
    
    def _log_audit_event(self, event_type: str, rollback_id: str, 
                        details: Dict[str, Any]):
        """Log audit trail entry"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'rollback_id': rollback_id,
            'details': details
        }
        self.audit_log.append(audit_entry)
        logger.info(f"Audit: {event_type} for {rollback_id}")
    
    async def save_audit_log(self, filepath: str = "migrations/rollback_audit.json"):
        """Save audit log to file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        async with aiofiles.open(filepath, 'w') as f:
            await f.write(json.dumps({
                'audit_log': self.audit_log,
                'rollback_points': self.rollback_points
            }, indent=2, default=str))
        
        logger.info(f"Saved audit log to {filepath}")
    
    def get_rollback_history(self) -> List[Dict[str, Any]]:
        """Get rollback operation history"""
        history = []
        for rb_id, info in self.rollback_points.items():
            history.append({
                'rollback_id': rb_id,
                'migration_id': info['migration_id'],
                'table_name': info['table_name'],
                'status': info['status'],
                'created_at': info['created_at'],
                'completed_at': info.get('completed_at'),
                'description': info['description']
            })
        return sorted(history, key=lambda x: x['created_at'], reverse=True)


class MigrationTransaction:
    """Context manager for migration with automatic rollback"""
    
    def __init__(self, rollback_manager: RollbackManager, 
                 migration_id: str, table_name: str, 
                 description: str):
        self.rollback_manager = rollback_manager
        self.migration_id = migration_id
        self.table_name = table_name
        self.description = description
        self.rollback_id = None
        self.session = None
        
    async def __aenter__(self):
        """Enter migration transaction"""
        engine = create_async_engine(self.rollback_manager.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self.session = async_session()
        
        # Create rollback point
        self.rollback_id = await self.rollback_manager.create_rollback_point(
            self.session, self.migration_id, self.table_name, self.description
        )
        
        await self.session.begin()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit migration transaction"""
        if exc_type is not None:
            # Error occurred - perform rollback
            logger.error(f"Migration failed: {exc_val}")
            await self.session.rollback()
            
            if self.rollback_id:
                await self.rollback_manager.execute_rollback(
                    self.rollback_id, RollbackType.FULL
                )
        else:
            # Success - commit transaction
            await self.session.commit()
            
        await self.session.close()
        await self.rollback_manager.save_audit_log()


# Example usage functions
async def example_migration_with_rollback():
    """Example of using rollback manager with migration"""
    from app.core.config import settings
    
    rollback_manager = RollbackManager(settings.DATABASE_URL)
    
    # Use transaction context for automatic rollback
    async with MigrationTransaction(
        rollback_manager,
        migration_id="client_migration_001",
        table_name="customers",
        description="Commercial client data migration"
    ) as session:
        # Perform migration operations
        # If any exception occurs, automatic rollback will be triggered
        pass


if __name__ == "__main__":
    # Test rollback functionality
    asyncio.run(example_migration_with_rollback())