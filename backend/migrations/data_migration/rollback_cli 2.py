#!/usr/bin/env python3
"""
Rollback CLI - Command-line interface for managing migration rollbacks
Author: Devin (Data Migration Specialist)
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from tabulate import tabulate
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings
from rollback_manager import RollbackManager, RollbackType


class RollbackCLI:
    """Command-line interface for rollback management"""
    
    def __init__(self):
        self.rollback_manager = RollbackManager(settings.DATABASE_URL)
    
    async def list_rollbacks(self):
        """List all available rollback points"""
        history = self.rollback_manager.get_rollback_history()
        
        if not history:
            print("No rollback points available.")
            return
        
        # Prepare data for tabular display
        table_data = []
        for item in history:
            table_data.append([
                item['rollback_id'][:20] + '...' if len(item['rollback_id']) > 20 else item['rollback_id'],
                item['migration_id'][:20] + '...' if len(item['migration_id']) > 20 else item['migration_id'],
                item['table_name'],
                item['status'],
                datetime.fromisoformat(item['created_at']).strftime('%Y-%m-%d %H:%M:%S'),
                item['description'][:30] + '...' if len(item['description']) > 30 else item['description']
            ])
        
        headers = ['Rollback ID', 'Migration ID', 'Table', 'Status', 'Created At', 'Description']
        print("\nAvailable Rollback Points:")
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    async def execute_rollback(self, rollback_id: str, rollback_type: str = 'full'):
        """Execute a rollback"""
        print(f"\nExecuting {rollback_type} rollback for: {rollback_id}")
        
        # Map string to enum
        type_map = {
            'full': RollbackType.FULL,
            'partial': RollbackType.PARTIAL,
            'backup': RollbackType.BACKUP_RESTORE,
            'transaction': RollbackType.TRANSACTION
        }
        
        if rollback_type not in type_map:
            print(f"Invalid rollback type: {rollback_type}")
            print(f"Valid types: {', '.join(type_map.keys())}")
            return
        
        try:
            # Confirm action
            confirm = input(f"\nAre you sure you want to execute a {rollback_type} rollback? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Rollback cancelled.")
                return
            
            # Execute rollback
            result = await self.rollback_manager.execute_rollback(
                rollback_id, type_map[rollback_type]
            )
            
            print(f"\n✅ Rollback executed successfully!")
            print(f"Result: {json.dumps(result, indent=2)}")
            
            # Verify rollback
            verification = await self.rollback_manager.verify_rollback(rollback_id)
            print(f"\nVerification: {verification['status']}")
            print(f"Current count: {verification['current_count']}")
            print(f"Expected count: {verification['expected_count']}")
            
        except Exception as e:
            print(f"\n❌ Rollback failed: {str(e)}")
    
    async def show_rollback_details(self, rollback_id: str):
        """Show detailed information about a rollback point"""
        if rollback_id not in self.rollback_manager.rollback_points:
            print(f"Rollback point not found: {rollback_id}")
            return
        
        info = self.rollback_manager.rollback_points[rollback_id]
        
        print(f"\nRollback Point Details:")
        print(f"{'='*50}")
        print(f"Rollback ID: {info['id']}")
        print(f"Migration ID: {info['migration_id']}")
        print(f"Table Name: {info['table_name']}")
        print(f"Description: {info['description']}")
        print(f"Status: {info['status']}")
        print(f"Created At: {info['created_at']}")
        
        if 'backup_info' in info:
            backup = info['backup_info']
            print(f"\nBackup Information:")
            print(f"  Row Count: {backup['row_count']}")
            print(f"  Checksum: {backup['checksum'][:16]}...")
            print(f"  File Path: {backup['file_path']}")
        
        if 'completed_at' in info:
            print(f"\nCompleted At: {info['completed_at']}")
        
        if 'error' in info:
            print(f"\nError: {info['error']}")
    
    async def show_audit_log(self, limit: int = 20):
        """Show audit log entries"""
        audit_log = self.rollback_manager.audit_log
        
        if not audit_log:
            # Try to load from file
            audit_file = "migrations/rollback_audit.json"
            if os.path.exists(audit_file):
                with open(audit_file, 'r') as f:
                    data = json.load(f)
                    audit_log = data.get('audit_log', [])
        
        if not audit_log:
            print("No audit log entries found.")
            return
        
        print(f"\nAudit Log (last {limit} entries):")
        print(f"{'='*80}")
        
        # Show most recent entries first
        for entry in reversed(audit_log[-limit:]):
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[{timestamp}] {entry['event_type']}")
            print(f"Rollback ID: {entry['rollback_id']}")
            if 'details' in entry:
                print(f"Details: {json.dumps(entry['details'], indent=2)}")
            print('-' * 40)
    
    async def create_manual_backup(self, table_name: str, description: str):
        """Create a manual backup point"""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                migration_id = f"manual_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                
                rollback_id = await self.rollback_manager.create_rollback_point(
                    session,
                    migration_id=migration_id,
                    table_name=table_name,
                    description=description
                )
                
                print(f"\n✅ Manual backup created successfully!")
                print(f"Rollback ID: {rollback_id}")
                print(f"Table: {table_name}")
                print(f"Description: {description}")
                
                # Save audit log
                await self.rollback_manager.save_audit_log()
                
        except Exception as e:
            print(f"\n❌ Failed to create backup: {str(e)}")
        finally:
            await engine.dispose()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Rollback management utility for database migrations'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    subparsers.add_parser('list', help='List all available rollback points')
    
    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute a rollback')
    execute_parser.add_argument('rollback_id', help='Rollback ID to execute')
    execute_parser.add_argument('--type', default='full', 
                              choices=['full', 'partial', 'backup', 'transaction'],
                              help='Type of rollback to perform')
    
    # Details command
    details_parser = subparsers.add_parser('details', help='Show rollback point details')
    details_parser.add_argument('rollback_id', help='Rollback ID to inspect')
    
    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Show audit log')
    audit_parser.add_argument('--limit', type=int, default=20, help='Number of entries to show')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create manual backup')
    backup_parser.add_argument('table', help='Table name to backup')
    backup_parser.add_argument('--description', default='Manual backup', help='Backup description')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = RollbackCLI()
    
    if args.command == 'list':
        await cli.list_rollbacks()
    elif args.command == 'execute':
        await cli.execute_rollback(args.rollback_id, args.type)
    elif args.command == 'details':
        await cli.show_rollback_details(args.rollback_id)
    elif args.command == 'audit':
        await cli.show_audit_log(args.limit)
    elif args.command == 'backup':
        await cli.create_manual_backup(args.table, args.description)


if __name__ == "__main__":
    asyncio.run(main())