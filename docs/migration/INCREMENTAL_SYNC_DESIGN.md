# Incremental Sync Mechanism Design

## Overview

This document outlines the design for incremental data synchronization between the legacy Lucky Gas system (ASP.NET/SQLite) and the new system (React/FastAPI/PostgreSQL) during the transition period.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Legacy System  │────▶│  Sync Service    │────▶│   New System    │
│  (SQLite/Big5)  │◀────│  (Python/Redis)  │◀────│ (PostgreSQL/UTF8)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
         ▲                       │                          ▲
         │                       ▼                          │
         │              ┌──────────────────┐               │
         └──────────────│  Change Tracking │───────────────┘
                        │   (Audit Logs)   │
                        └──────────────────┘
```

## Key Components

### 1. Change Detection Mechanism

#### Option A: Timestamp-Based (Recommended)
```python
class TimestampTracker:
    """Track changes using updated_at timestamps"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.sync_prefix = "sync:timestamp:"
    
    async def get_last_sync_time(self, table: str) -> datetime:
        """Get last successful sync timestamp for a table"""
        key = f"{self.sync_prefix}{table}"
        timestamp = await self.redis.get(key)
        if timestamp:
            return datetime.fromisoformat(timestamp)
        return datetime(2000, 1, 1)  # Epoch start
    
    async def set_last_sync_time(self, table: str, timestamp: datetime):
        """Update last sync timestamp after successful sync"""
        key = f"{self.sync_prefix}{table}"
        await self.redis.set(key, timestamp.isoformat())
    
    def get_changes_query(self, table: str, last_sync: datetime) -> str:
        """Generate SQL to fetch changed records"""
        return f"""
        SELECT * FROM {table}
        WHERE updated_at > '{last_sync.isoformat()}'
        ORDER BY updated_at ASC
        """
```

#### Option B: Trigger-Based Change Tracking
```sql
-- Legacy system triggers (SQLite)
CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    operation TEXT NOT NULL, -- INSERT, UPDATE, DELETE
    changed_data TEXT, -- JSON of changed fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0
);

-- Trigger example for clients table
CREATE TRIGGER clients_sync_insert
AFTER INSERT ON clients
BEGIN
    INSERT INTO sync_queue (table_name, record_id, operation, changed_data)
    VALUES ('clients', NEW.id, 'INSERT', json_object(
        'client_code', NEW.client_code,
        'name', NEW.name,
        'address', NEW.address
    ));
END;
```

### 2. Sync Service Implementation

```python
# backend/app/services/incremental_sync_service.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
import aioredis
import sqlite3
import pandas as pd

from app.utils.encoding_converter import Big5ToUTF8Converter
from app.core.database import get_async_session

logger = logging.getLogger(__name__)


class IncrementalSyncService:
    """
    Handles incremental synchronization between legacy and new systems.
    Supports bidirectional sync with conflict resolution.
    """
    
    def __init__(
        self,
        legacy_db_path: str,
        redis_url: str = "redis://localhost:6379",
        sync_interval_minutes: int = 5
    ):
        self.legacy_db_path = legacy_db_path
        self.redis_url = redis_url
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        self.converter = Big5ToUTF8Converter()
        self.redis = None
        self.is_running = False
        
        # Table sync configuration
        self.sync_config = {
            'clients': {
                'legacy_to_new': True,
                'new_to_legacy': False,  # One-way for customers
                'id_mapping_key': 'sync:id_map:customers',
                'timestamp_key': 'sync:timestamp:clients',
                'text_fields': ['name', 'address', 'notes', 'contact_person'],
                'conflict_resolution': 'newest_wins'
            },
            'deliveries': {
                'legacy_to_new': True,
                'new_to_legacy': True,  # Bidirectional for orders
                'id_mapping_key': 'sync:id_map:orders',
                'timestamp_key': 'sync:timestamp:deliveries',
                'text_fields': ['notes'],
                'conflict_resolution': 'newest_wins'
            },
            'drivers': {
                'legacy_to_new': True,
                'new_to_legacy': False,
                'id_mapping_key': 'sync:id_map:drivers',
                'timestamp_key': 'sync:timestamp:drivers',
                'text_fields': ['name', 'familiar_areas'],
                'conflict_resolution': 'newest_wins'
            }
        }
        
        # Sync statistics
        self.stats = {
            'last_sync': None,
            'records_synced': 0,
            'conflicts_resolved': 0,
            'errors': 0
        }
    
    async def initialize(self):
        """Initialize Redis connection and sync state."""
        self.redis = await aioredis.create_redis_pool(self.redis_url)
        logger.info("Incremental sync service initialized")
    
    async def start_sync_loop(self):
        """Start the continuous sync loop."""
        self.is_running = True
        logger.info(f"Starting sync loop with {self.sync_interval.seconds}s interval")
        
        while self.is_running:
            try:
                await self.run_sync_cycle()
                await asyncio.sleep(self.sync_interval.seconds)
            except Exception as e:
                logger.error(f"Sync cycle failed: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def stop_sync_loop(self):
        """Stop the sync loop gracefully."""
        self.is_running = False
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
    
    async def run_sync_cycle(self):
        """Run a single sync cycle for all configured tables."""
        logger.info("Starting sync cycle")
        cycle_start = datetime.now()
        
        async for session in get_async_session():
            try:
                for table_name, config in self.sync_config.items():
                    if config['legacy_to_new']:
                        await self.sync_legacy_to_new(table_name, config, session)
                    
                    if config['new_to_legacy']:
                        await self.sync_new_to_legacy(table_name, config, session)
                
                await session.commit()
                self.stats['last_sync'] = datetime.now()
                
                duration = datetime.now() - cycle_start
                logger.info(f"Sync cycle completed in {duration.seconds}s")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Sync cycle error: {e}")
                raise
            finally:
                await session.close()
    
    async def sync_legacy_to_new(
        self,
        table_name: str,
        config: Dict[str, Any],
        session: AsyncSession
    ):
        """Sync changes from legacy to new system."""
        # Get last sync timestamp
        last_sync = await self.get_last_sync_time(config['timestamp_key'])
        
        # Fetch changed records from legacy
        legacy_changes = self.fetch_legacy_changes(table_name, last_sync)
        
        if legacy_changes.empty:
            return
        
        logger.info(f"Found {len(legacy_changes)} changes in legacy {table_name}")
        
        # Convert encoding
        legacy_changes = self.converter.convert_dataframe(
            legacy_changes,
            columns=config['text_fields']
        )
        
        # Process each change
        for _, record in legacy_changes.iterrows():
            try:
                await self.process_legacy_record(
                    table_name, record, config, session
                )
                self.stats['records_synced'] += 1
            except Exception as e:
                logger.error(f"Failed to sync record {record.get('id')}: {e}")
                self.stats['errors'] += 1
        
        # Update sync timestamp
        if not legacy_changes.empty:
            max_timestamp = legacy_changes['updated_at'].max()
            await self.set_last_sync_time(
                config['timestamp_key'],
                pd.to_datetime(max_timestamp)
            )
    
    async def sync_new_to_legacy(
        self,
        table_name: str,
        config: Dict[str, Any],
        session: AsyncSession
    ):
        """Sync changes from new system to legacy (for bidirectional tables)."""
        # Implementation for new-to-legacy sync
        # This is more complex as it requires writing to SQLite with Big5 encoding
        pass
    
    def fetch_legacy_changes(
        self,
        table_name: str,
        last_sync: datetime
    ) -> pd.DataFrame:
        """Fetch changed records from legacy database."""
        conn = sqlite3.connect(self.legacy_db_path)
        
        query = f"""
        SELECT * FROM {table_name}
        WHERE updated_at > ?
        ORDER BY updated_at ASC
        LIMIT 1000
        """
        
        df = pd.read_sql_query(
            query,
            conn,
            params=(last_sync.isoformat(),)
        )
        
        conn.close()
        return df
    
    async def process_legacy_record(
        self,
        table_name: str,
        record: pd.Series,
        config: Dict[str, Any],
        session: AsyncSession
    ):
        """Process a single legacy record and sync to new system."""
        # Get ID mapping
        legacy_id = record['id']
        new_id = await self.get_id_mapping(config['id_mapping_key'], legacy_id)
        
        if table_name == 'clients':
            await self.sync_customer_record(record, new_id, session)
        elif table_name == 'deliveries':
            await self.sync_order_record(record, new_id, session)
        elif table_name == 'drivers':
            await self.sync_driver_record(record, new_id, session)
    
    async def sync_customer_record(
        self,
        record: pd.Series,
        existing_id: Optional[int],
        session: AsyncSession
    ):
        """Sync a customer record."""
        from app.models import Customer
        
        if existing_id:
            # Update existing
            customer = await session.get(Customer, existing_id)
            if customer:
                # Check for conflicts
                if customer.updated_at > pd.to_datetime(record['updated_at']):
                    logger.info(f"Skipping customer {record['client_code']} - newer version exists")
                    return
                
                # Update fields
                customer.name = record['invoice_title'] or record['short_name']
                customer.address = record['address']
                customer.phone = self._extract_phone(record.get('contact_person', ''))
                customer.notes = record.get('notes')
                customer.updated_at = datetime.now()
        else:
            # Create new
            customer = Customer(
                customer_code=record['client_code'],
                name=record['invoice_title'] or record['short_name'],
                short_name=record['short_name'],
                address=record['address'],
                phone=self._extract_phone(record.get('contact_person', '')),
                # ... map other fields
            )
            session.add(customer)
            await session.flush()
            
            # Store ID mapping
            await self.set_id_mapping(
                self.sync_config['clients']['id_mapping_key'],
                record['id'],
                customer.id
            )
    
    # Redis helper methods
    
    async def get_last_sync_time(self, key: str) -> datetime:
        """Get last sync timestamp from Redis."""
        timestamp = await self.redis.get(key)
        if timestamp:
            return datetime.fromisoformat(timestamp.decode())
        return datetime(2000, 1, 1)
    
    async def set_last_sync_time(self, key: str, timestamp: datetime):
        """Set last sync timestamp in Redis."""
        await self.redis.set(key, timestamp.isoformat())
    
    async def get_id_mapping(self, key: str, legacy_id: int) -> Optional[int]:
        """Get new system ID for a legacy ID."""
        new_id = await self.redis.hget(key, str(legacy_id))
        return int(new_id) if new_id else None
    
    async def set_id_mapping(self, key: str, legacy_id: int, new_id: int):
        """Store ID mapping between systems."""
        await self.redis.hset(key, str(legacy_id), str(new_id))
    
    def _extract_phone(self, contact_info: str) -> Optional[str]:
        """Extract phone number from contact info."""
        import re
        if not contact_info:
            return None
        
        phone_pattern = r'(09\d{2}[-\s]?\d{3}[-\s]?\d{3}|0[2-8][-\s]?\d{4}[-\s]?\d{4})'
        match = re.search(phone_pattern, contact_info)
        return match.group(1).replace(' ', '').replace('-', '') if match else None
```

### 3. Conflict Resolution Strategies

```python
class ConflictResolver:
    """Handles conflicts during bidirectional sync."""
    
    @staticmethod
    def newest_wins(legacy_record: Dict, new_record: Dict) -> Dict:
        """Resolution: Keep the record with the latest timestamp."""
        legacy_time = pd.to_datetime(legacy_record['updated_at'])
        new_time = new_record['updated_at']
        
        if legacy_time > new_time:
            return legacy_record
        return new_record
    
    @staticmethod
    def legacy_wins(legacy_record: Dict, new_record: Dict) -> Dict:
        """Resolution: Always prefer legacy system data."""
        return legacy_record
    
    @staticmethod
    def new_wins(legacy_record: Dict, new_record: Dict) -> Dict:
        """Resolution: Always prefer new system data."""
        return new_record
    
    @staticmethod
    def merge_fields(legacy_record: Dict, new_record: Dict, merge_rules: Dict) -> Dict:
        """Resolution: Merge specific fields based on rules."""
        merged = new_record.copy()
        
        for field, rule in merge_rules.items():
            if rule == 'prefer_legacy':
                merged[field] = legacy_record.get(field)
            elif rule == 'prefer_new':
                merged[field] = new_record.get(field)
            elif rule == 'combine':
                # Combine values (e.g., notes)
                legacy_val = legacy_record.get(field, '')
                new_val = new_record.get(field, '')
                merged[field] = f"{new_val}\n---\n{legacy_val}".strip()
        
        return merged
```

### 4. Monitoring and Health Checks

```python
class SyncMonitor:
    """Monitor sync health and performance."""
    
    def __init__(self, sync_service: IncrementalSyncService):
        self.sync_service = sync_service
        self.alerts = []
    
    async def check_sync_health(self) -> Dict[str, Any]:
        """Perform health checks on sync process."""
        health_status = {
            'status': 'healthy',
            'last_sync': self.sync_service.stats['last_sync'],
            'lag_seconds': 0,
            'error_rate': 0,
            'checks': []
        }
        
        # Check 1: Sync lag
        if self.sync_service.stats['last_sync']:
            lag = datetime.now() - self.sync_service.stats['last_sync']
            health_status['lag_seconds'] = lag.total_seconds()
            
            if lag > timedelta(minutes=30):
                health_status['status'] = 'critical'
                health_status['checks'].append({
                    'name': 'sync_lag',
                    'status': 'critical',
                    'message': f'Sync lag is {lag.total_seconds()/60:.1f} minutes'
                })
        
        # Check 2: Error rate
        total_ops = self.sync_service.stats['records_synced'] + self.sync_service.stats['errors']
        if total_ops > 0:
            error_rate = self.sync_service.stats['errors'] / total_ops
            health_status['error_rate'] = error_rate
            
            if error_rate > 0.05:  # 5% error threshold
                health_status['status'] = 'warning'
                health_status['checks'].append({
                    'name': 'error_rate',
                    'status': 'warning',
                    'message': f'Error rate is {error_rate:.1%}'
                })
        
        # Check 3: Data consistency
        consistency_check = await self.check_data_consistency()
        health_status['checks'].append(consistency_check)
        
        return health_status
    
    async def check_data_consistency(self) -> Dict[str, Any]:
        """Verify data consistency between systems."""
        # Sample check: Compare record counts
        legacy_counts = self.get_legacy_record_counts()
        new_counts = await self.get_new_record_counts()
        
        discrepancies = []
        for table, legacy_count in legacy_counts.items():
            new_count = new_counts.get(table, 0)
            diff = abs(legacy_count - new_count)
            
            if diff > legacy_count * 0.01:  # 1% tolerance
                discrepancies.append({
                    'table': table,
                    'legacy': legacy_count,
                    'new': new_count,
                    'difference': diff
                })
        
        if discrepancies:
            return {
                'name': 'data_consistency',
                'status': 'warning',
                'message': f'Found {len(discrepancies)} table(s) with count discrepancies',
                'details': discrepancies
            }
        
        return {
            'name': 'data_consistency',
            'status': 'healthy',
            'message': 'Data counts are consistent'
        }
```

### 5. Deployment Configuration

```yaml
# docker-compose.sync.yml
version: '3.8'

services:
  sync-service:
    build:
      context: ./backend
      dockerfile: Dockerfile.sync
    environment:
      - LEGACY_DB_PATH=/data/luckygas.db
      - DATABASE_URL=postgresql://luckygas:password@db:5432/luckygas
      - REDIS_URL=redis://redis:6379
      - SYNC_INTERVAL_MINUTES=5
      - LOG_LEVEL=INFO
    volumes:
      - ./raw/luckygas.db:/data/luckygas.db:ro
      - ./logs/sync:/app/logs
    depends_on:
      - db
      - redis
    restart: unless-stopped
    
  sync-monitor:
    build:
      context: ./backend
      dockerfile: Dockerfile.monitor
    ports:
      - "9090:9090"  # Prometheus metrics
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - sync-service
      - redis
```

### 6. CLI Management Tool

```python
# backend/app/cli/sync_manager.py
import click
import asyncio
from app.services.incremental_sync_service import IncrementalSyncService

@click.group()
def cli():
    """Lucky Gas Sync Management CLI"""
    pass

@cli.command()
@click.option('--legacy-db', required=True, help='Path to legacy database')
@click.option('--interval', default=5, help='Sync interval in minutes')
def start(legacy_db: str, interval: int):
    """Start the incremental sync service."""
    async def run():
        service = IncrementalSyncService(legacy_db, sync_interval_minutes=interval)
        await service.initialize()
        await service.start_sync_loop()
    
    asyncio.run(run())

@cli.command()
@click.option('--legacy-db', required=True, help='Path to legacy database')
def sync_once(legacy_db: str):
    """Run a single sync cycle."""
    async def run():
        service = IncrementalSyncService(legacy_db)
        await service.initialize()
        await service.run_sync_cycle()
        await service.stop_sync_loop()
    
    asyncio.run(run())

@cli.command()
def status():
    """Check sync service status."""
    async def run():
        # Connect to Redis and check status
        import aioredis
        redis = await aioredis.create_redis_pool('redis://localhost:6379')
        
        # Get sync timestamps
        tables = ['clients', 'deliveries', 'drivers']
        for table in tables:
            key = f'sync:timestamp:{table}'
            timestamp = await redis.get(key)
            if timestamp:
                print(f"{table}: Last synced at {timestamp.decode()}")
            else:
                print(f"{table}: Never synced")
        
        redis.close()
        await redis.wait_closed()
    
    asyncio.run(run())

if __name__ == '__main__':
    cli()
```

## Implementation Phases

### Phase 1: One-way Sync (Legacy → New)
1. Implement timestamp tracking
2. Create sync service for read-only sync
3. Deploy and monitor for 1 week
4. Validate data consistency

### Phase 2: Bidirectional Sync
1. Add change tracking to new system
2. Implement new-to-legacy sync
3. Add conflict resolution
4. Test with non-critical data

### Phase 3: Production Deployment
1. Set up monitoring and alerting
2. Create runbooks for common issues
3. Train operations team
4. Deploy with gradual rollout

## Monitoring & Alerting

### Key Metrics
- Sync lag (time since last sync)
- Records synced per cycle
- Error rate
- Conflict resolution rate
- Processing time per table

### Alert Thresholds
- Critical: Sync lag > 30 minutes
- Warning: Error rate > 5%
- Info: Conflict rate > 10%

## Rollback Plan

1. **Stop sync service**: `docker-compose stop sync-service`
2. **Check data integrity**: Run consistency checks
3. **Restore from backup**: If data corruption detected
4. **Resume manual processes**: Fallback to manual data entry

## Performance Considerations

### Optimization Strategies
1. **Batch processing**: Process up to 1000 records per cycle
2. **Parallel table sync**: Sync independent tables concurrently
3. **Index optimization**: Ensure updated_at columns are indexed
4. **Connection pooling**: Reuse database connections
5. **Redis pipelining**: Batch Redis operations

### Expected Performance
- Sync cycle time: < 30 seconds for normal load
- Records per second: 100-500 depending on size
- Memory usage: < 500MB
- CPU usage: < 25% of single core

## Security Considerations

1. **Read-only access**: Legacy system access is read-only
2. **Encryption**: Use TLS for database connections
3. **Authentication**: Service accounts with minimal permissions
4. **Audit logging**: Log all sync operations
5. **Data validation**: Validate all data before insertion