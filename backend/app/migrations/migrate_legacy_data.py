#!/usr/bin/env python3
"""
Legacy data migration script for Lucky Gas system
Migrates data from SQLite (Big5) to PostgreSQL (UTF-8)
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import sqlite3
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
import click

from app.core.database import get_async_session
from app.utils.encoding_converter import Big5ToUTF8Converter, validate_taiwan_data
from app.models import (
    Customer, User, Order, OrderItem, GasProduct,
    Route, Vehicle, DeliveryHistory
)
from app.models.order import OrderStatus, PaymentStatus
from app.models.user import UserRole

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LegacyDataMigrator:
    """
    Handles migration of data from legacy SQLite database to new PostgreSQL system.
    """
    
    def __init__(self, legacy_db_path: str, batch_size: int = 1000):
        """
        Initialize migrator with database paths and settings.
        
        Args:
            legacy_db_path: Path to legacy SQLite database
            batch_size: Number of records to process in each batch
        """
        self.legacy_db_path = legacy_db_path
        self.batch_size = batch_size
        self.converter = Big5ToUTF8Converter(fallback_errors='replace')
        
        # Mapping tables for ID conversions
        self.id_mappings = {
            'customers': {},  # old_id -> new_id
            'users': {},      # old_driver_id -> new_user_id
            'products': {},   # cylinder_size -> product_id
            'vehicles': {},   # old_id -> new_id
        }
        
        # Statistics
        self.stats = {
            'customers': {'total': 0, 'migrated': 0, 'failed': 0},
            'orders': {'total': 0, 'migrated': 0, 'failed': 0},
            'users': {'total': 0, 'migrated': 0, 'failed': 0},
            'vehicles': {'total': 0, 'migrated': 0, 'failed': 0},
        }
        
        # Error tracking
        self.errors = []
    
    async def initialize_products(self, session: AsyncSession):
        """
        Create standard gas products if they don't exist.
        """
        standard_products = [
            {'size': 50, 'name': '50公斤桶裝瓦斯', 'code': 'GAS-50KG', 'price': 2500},
            {'size': 20, 'name': '20公斤桶裝瓦斯', 'code': 'GAS-20KG', 'price': 1200},
            {'size': 16, 'name': '16公斤桶裝瓦斯', 'code': 'GAS-16KG', 'price': 1000},
            {'size': 10, 'name': '10公斤桶裝瓦斯', 'code': 'GAS-10KG', 'price': 700},
            {'size': 4, 'name': '4公斤桶裝瓦斯', 'code': 'GAS-4KG', 'price': 350},
            # Special variants
            {'size': 20, 'name': '20公斤營業用瓦斯', 'code': 'GAS-20KG-BIZ', 'price': 1150},
            {'size': 16, 'name': '16公斤營業用瓦斯', 'code': 'GAS-16KG-BIZ', 'price': 950},
            {'size': 20, 'name': '20公斤好運瓦斯', 'code': 'GAS-20KG-LUCKY', 'price': 1180},
            {'size': 16, 'name': '16公斤好運瓦斯', 'code': 'GAS-16KG-LUCKY', 'price': 980},
            {'size': 10, 'name': '10公斤平安桶', 'code': 'GAS-10KG-SAFE', 'price': 680},
            {'size': 4, 'name': '4公斤幸福罐', 'code': 'GAS-4KG-HAPPY', 'price': 340},
        ]
        
        for product_data in standard_products:
            # Check if product exists
            result = await session.execute(
                select(GasProduct).where(GasProduct.product_code == product_data['code'])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                product = GasProduct(
                    product_code=product_data['code'],
                    product_name=product_data['name'],
                    display_name=product_data['name'],
                    cylinder_size=product_data['size'],
                    unit_price=product_data['price'],
                    deposit_amount=product_data['size'] * 60,  # Rough deposit calculation
                    is_available=True,
                    category='standard' if 'BIZ' not in product_data['code'] else 'business'
                )
                session.add(product)
                
            # Store mapping
            self.id_mappings['products'][product_data['size']] = product_data['code']
        
        await session.commit()
        logger.info("Initialized gas products")
    
    def read_legacy_table(self, table_name: str, text_columns: List[str]) -> pd.DataFrame:
        """
        Read and convert a table from legacy database.
        
        Args:
            table_name: Name of table to read
            text_columns: List of columns that contain text to convert
            
        Returns:
            DataFrame with converted data
        """
        conn = sqlite3.connect(self.legacy_db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        
        # Convert text columns from Big5 to UTF-8
        df_converted = self.converter.convert_dataframe(df, columns=text_columns)
        
        logger.info(f"Read {len(df_converted)} records from {table_name}")
        return df_converted
    
    async def migrate_customers(self, session: AsyncSession) -> Dict[int, int]:
        """
        Migrate customers from legacy clients table.
        
        Returns:
            Mapping of old client IDs to new customer IDs
        """
        logger.info("Starting customer migration...")
        
        # Read legacy data
        df = self.read_legacy_table('clients', [
            'client_code', 'invoice_title', 'short_name', 'address',
            'name', 'contact_person', 'district', 'notes', 'area',
            'primary_usage_area', 'secondary_usage_area', 'switch_model',
            'client_type', 'holiday', 'payment_file', 'pricing_method'
        ])
        
        self.stats['customers']['total'] = len(df)
        
        # Process in batches
        for start_idx in range(0, len(df), self.batch_size):
            batch = df.iloc[start_idx:start_idx + self.batch_size]
            
            for _, row in batch.iterrows():
                try:
                    # Parse phone from contact info if available
                    phone = self._extract_phone(row.get('contact_person', ''))
                    
                    # Validate data
                    if not validate_taiwan_data(row['address'], 'address'):
                        logger.warning(f"Invalid address for customer {row['client_code']}: {row['address']}")
                    
                    # Create customer
                    customer = Customer(
                        customer_code=row['client_code'],
                        name=row['invoice_title'] or row['short_name'],
                        short_name=row['short_name'],
                        address=row['address'],
                        phone=phone,
                        contact_person=row.get('contact_person'),
                        tax_id=row.get('tax_id') if validate_taiwan_data(row.get('tax_id', ''), 'tax_id') else None,
                        customer_type='corporate' if row.get('is_corporate') else 'residential',
                        district=row.get('district'),
                        area=row.get('area'),
                        latitude=float(row['latitude']) if pd.notna(row.get('latitude')) else None,
                        longitude=float(row['longitude']) if pd.notna(row.get('longitude')) else None,
                        
                        # Business fields
                        is_active=bool(row.get('is_active', True)),
                        is_terminated=bool(row.get('is_terminated', False)),
                        payment_method=self._map_payment_method(row.get('payment_method')),
                        pricing_type=row.get('pricing_method', 'standard'),
                        
                        # Delivery preferences
                        delivery_time_preference=row.get('delivery_time_preference'),
                        delivery_time_start=self._parse_delivery_hours(row, 'start'),
                        delivery_time_end=self._parse_delivery_hours(row, 'end'),
                        needs_same_day_delivery=bool(row.get('needs_same_day_delivery')),
                        
                        # Equipment
                        has_flow_meter=bool(row.get('has_flow_meter')),
                        has_switch=bool(row.get('has_switch')),
                        
                        # Cylinder inventory (stored as JSON)
                        cylinder_inventory={
                            '50kg': int(row.get('cylinder_50kg', 0)),
                            '20kg': int(row.get('cylinder_20kg', 0)),
                            '16kg': int(row.get('cylinder_16kg', 0)),
                            '10kg': int(row.get('cylinder_10kg', 0)),
                            '4kg': int(row.get('cylinder_4kg', 0)),
                        },
                        
                        # Usage statistics
                        monthly_delivery_volume=float(row.get('monthly_delivery_volume', 0)),
                        daily_usage_avg=float(row.get('daily_usage_avg', 0)),
                        
                        # Metadata
                        notes=row.get('notes'),
                        created_at=pd.to_datetime(row.get('created_at', datetime.now())),
                        updated_at=pd.to_datetime(row.get('updated_at', datetime.now()))
                    )
                    
                    session.add(customer)
                    await session.flush()
                    
                    # Store ID mapping
                    self.id_mappings['customers'][row['id']] = customer.id
                    self.stats['customers']['migrated'] += 1
                    
                except Exception as e:
                    self.stats['customers']['failed'] += 1
                    self.errors.append({
                        'table': 'customers',
                        'record': row['client_code'],
                        'error': str(e)
                    })
                    logger.error(f"Failed to migrate customer {row['client_code']}: {e}")
            
            # Commit batch
            await session.commit()
            logger.info(f"Migrated customer batch {start_idx}-{start_idx + len(batch)}")
        
        logger.info(f"Customer migration complete: {self.stats['customers']}")
        return self.id_mappings['customers']
    
    async def migrate_drivers(self, session: AsyncSession) -> Dict[int, int]:
        """
        Migrate drivers as users with driver role.
        
        Returns:
            Mapping of old driver IDs to new user IDs
        """
        logger.info("Starting driver migration...")
        
        # Read legacy data
        df = self.read_legacy_table('drivers', [
            'name', 'phone', 'employee_id', 'license_type', 'familiar_areas'
        ])
        
        self.stats['users']['total'] = len(df)
        
        for _, row in df.iterrows():
            try:
                # Generate email from employee ID
                email = f"{row['employee_id']}@luckygas.tw"
                
                # Create user with driver role
                user = User(
                    email=email,
                    full_name=row['name'],
                    phone=row.get('phone'),
                    employee_id=row['employee_id'],
                    role=UserRole.DRIVER,
                    is_active=bool(row.get('is_active', True)),
                    
                    # Driver-specific fields
                    driver_license_type=row.get('license_type'),
                    driver_experience_years=int(row.get('experience_years', 0)),
                    driver_familiar_areas=self._parse_familiar_areas(row.get('familiar_areas')),
                    is_available=bool(row.get('is_available', True)),
                    
                    created_at=pd.to_datetime(row.get('created_at', datetime.now())),
                    updated_at=pd.to_datetime(row.get('updated_at', datetime.now()))
                )
                
                # Set temporary password (must be changed on first login)
                user.set_password(f"LuckyGas@{row['employee_id']}")
                
                session.add(user)
                await session.flush()
                
                # Store ID mapping
                self.id_mappings['users'][row['id']] = user.id
                self.stats['users']['migrated'] += 1
                
            except Exception as e:
                self.stats['users']['failed'] += 1
                self.errors.append({
                    'table': 'drivers',
                    'record': row['employee_id'],
                    'error': str(e)
                })
                logger.error(f"Failed to migrate driver {row['employee_id']}: {e}")
        
        await session.commit()
        logger.info(f"Driver migration complete: {self.stats['users']}")
        return self.id_mappings['users']
    
    async def migrate_vehicles(self, session: AsyncSession) -> Dict[int, int]:
        """
        Migrate vehicles table.
        
        Returns:
            Mapping of old vehicle IDs to new vehicle IDs
        """
        logger.info("Starting vehicle migration...")
        
        # Read legacy data
        df = self.read_legacy_table('vehicles', ['plate_number', 'vehicle_type'])
        
        self.stats['vehicles']['total'] = len(df)
        
        for _, row in df.iterrows():
            try:
                # Map driver ID if assigned
                driver_id = None
                if pd.notna(row.get('driver_id')):
                    driver_id = self.id_mappings['users'].get(int(row['driver_id']))
                
                vehicle = Vehicle(
                    plate_number=row['plate_number'],
                    vehicle_type=row['vehicle_type'],
                    is_active=bool(row.get('is_active', True)),
                    is_available=bool(row.get('is_available', True)),
                    assigned_driver_id=driver_id,
                    
                    # Capacity
                    capacity_50kg=int(row.get('max_cylinders_50kg', 0)),
                    capacity_20kg=int(row.get('max_cylinders_20kg', 0)),
                    capacity_16kg=int(row.get('max_cylinders_16kg', 0)),
                    capacity_10kg=int(row.get('max_cylinders_10kg', 0)),
                    capacity_4kg=int(row.get('max_cylinders_4kg', 0)),
                    
                    # Maintenance
                    last_maintenance_date=pd.to_datetime(row.get('last_maintenance')) if pd.notna(row.get('last_maintenance')) else None,
                    next_maintenance_date=pd.to_datetime(row.get('next_maintenance')) if pd.notna(row.get('next_maintenance')) else None,
                    
                    created_at=pd.to_datetime(row.get('created_at', datetime.now())),
                    updated_at=pd.to_datetime(row.get('updated_at', datetime.now()))
                )
                
                session.add(vehicle)
                await session.flush()
                
                # Store ID mapping
                self.id_mappings['vehicles'][row['id']] = vehicle.id
                self.stats['vehicles']['migrated'] += 1
                
            except Exception as e:
                self.stats['vehicles']['failed'] += 1
                self.errors.append({
                    'table': 'vehicles',
                    'record': row['plate_number'],
                    'error': str(e)
                })
                logger.error(f"Failed to migrate vehicle {row['plate_number']}: {e}")
        
        await session.commit()
        logger.info(f"Vehicle migration complete: {self.stats['vehicles']}")
        return self.id_mappings['vehicles']
    
    async def migrate_orders(self, session: AsyncSession):
        """
        Migrate deliveries as orders with order items.
        """
        logger.info("Starting order migration...")
        
        # Read legacy data
        df = self.read_legacy_table('deliveries', ['notes'])
        
        self.stats['orders']['total'] = len(df)
        
        # Process in batches
        for start_idx in range(0, len(df), self.batch_size):
            batch = df.iloc[start_idx:start_idx + self.batch_size]
            
            for _, row in batch.iterrows():
                try:
                    # Map IDs
                    customer_id = self.id_mappings['customers'].get(row['client_id'])
                    if not customer_id:
                        logger.warning(f"Customer not found for delivery {row['id']}")
                        continue
                    
                    driver_id = None
                    if pd.notna(row.get('driver_id')):
                        driver_id = self.id_mappings['users'].get(int(row['driver_id']))
                    
                    # Create order
                    order_number = f"MIG-{row['scheduled_date']}-{row['id']:06d}"
                    
                    order = Order(
                        order_number=order_number,
                        customer_id=customer_id,
                        scheduled_date=pd.to_datetime(row['scheduled_date']).date(),
                        delivery_time_start=self._parse_time(row.get('scheduled_time_start')),
                        delivery_time_end=self._parse_time(row.get('scheduled_time_end')),
                        
                        # Status mapping
                        status=self._map_order_status(row.get('status', 'pending')),
                        payment_status=PaymentStatus.UNPAID,  # Default, update later
                        
                        # Delivery info
                        driver_id=driver_id,
                        route_sequence=int(row.get('route_sequence', 0)) if pd.notna(row.get('route_sequence')) else None,
                        estimated_distance=float(row.get('distance_km', 0)) if pd.notna(row.get('distance_km')) else None,
                        estimated_duration=int(row.get('estimated_duration_minutes', 0)) if pd.notna(row.get('estimated_duration_minutes')) else None,
                        
                        # Delivery confirmation
                        delivered_at=pd.to_datetime(row['actual_delivery_time']) if pd.notna(row.get('actual_delivery_time')) else None,
                        signature_url=row.get('signature_url'),
                        
                        # Notes
                        delivery_notes=row.get('notes'),
                        
                        # Calculate totals later
                        total_amount=0,
                        final_amount=0,
                        
                        created_at=pd.to_datetime(row.get('created_at', datetime.now())),
                        updated_at=pd.to_datetime(row.get('updated_at', datetime.now()))
                    )
                    
                    session.add(order)
                    await session.flush()
                    
                    # Create order items from cylinder quantities
                    total_amount = await self._create_order_items(session, order.id, row)
                    
                    # Update order totals
                    order.total_amount = total_amount
                    order.final_amount = total_amount  # No discount in legacy data
                    
                    self.stats['orders']['migrated'] += 1
                    
                except Exception as e:
                    self.stats['orders']['failed'] += 1
                    self.errors.append({
                        'table': 'orders',
                        'record': f"delivery_{row['id']}",
                        'error': str(e)
                    })
                    logger.error(f"Failed to migrate order {row['id']}: {e}")
            
            # Commit batch
            await session.commit()
            logger.info(f"Migrated order batch {start_idx}-{start_idx + len(batch)}")
        
        logger.info(f"Order migration complete: {self.stats['orders']}")
    
    async def _create_order_items(self, session: AsyncSession, order_id: int, delivery_row: pd.Series) -> float:
        """
        Create order items from legacy delivery cylinder quantities.
        
        Returns:
            Total amount for the order
        """
        total_amount = 0.0
        
        # Map cylinder quantities to products
        cylinder_mappings = [
            ('delivered_50kg', 'returned_50kg', 'GAS-50KG', 2500),
            ('delivered_20kg', 'returned_20kg', 'GAS-20KG', 1200),
            ('delivered_16kg', 'returned_16kg', 'GAS-16KG', 1000),
            ('delivered_10kg', 'returned_10kg', 'GAS-10KG', 700),
            ('delivered_4kg', 'returned_4kg', 'GAS-4KG', 350),
        ]
        
        for delivered_col, returned_col, product_code, unit_price in cylinder_mappings:
            delivered_qty = int(delivery_row.get(delivered_col, 0)) if pd.notna(delivery_row.get(delivered_col)) else 0
            returned_qty = int(delivery_row.get(returned_col, 0)) if pd.notna(delivery_row.get(returned_col)) else 0
            
            if delivered_qty > 0:
                # Get product
                result = await session.execute(
                    select(GasProduct).where(GasProduct.product_code == product_code)
                )
                product = result.scalar_one_or_none()
                
                if product:
                    order_item = OrderItem(
                        order_id=order_id,
                        gas_product_id=product.id,
                        quantity=delivered_qty,
                        unit_price=unit_price,
                        is_exchange=returned_qty > 0,
                        empty_received=returned_qty,
                        subtotal=delivered_qty * unit_price,
                        final_amount=delivered_qty * unit_price  # No discount in legacy
                    )
                    session.add(order_item)
                    total_amount += order_item.final_amount
        
        return total_amount
    
    # Helper methods
    
    def _extract_phone(self, contact_info: str) -> Optional[str]:
        """Extract phone number from contact person field."""
        if not contact_info:
            return None
        
        import re
        # Look for Taiwan phone patterns
        phone_pattern = r'(09\d{2}[-\s]?\d{3}[-\s]?\d{3}|0[2-8][-\s]?\d{4}[-\s]?\d{4})'
        match = re.search(phone_pattern, contact_info)
        
        if match:
            return match.group(1).replace(' ', '').replace('-', '')
        
        return None
    
    def _map_payment_method(self, legacy_method: str) -> str:
        """Map legacy payment method to new enum."""
        mapping = {
            'cash': 'cash',
            'credit': 'monthly',
            'transfer': 'transfer',
            '現金': 'cash',
            '月結': 'monthly',
            '轉帳': 'transfer'
        }
        return mapping.get(legacy_method, 'cash')
    
    def _parse_delivery_hours(self, row: pd.Series, time_type: str) -> Optional[str]:
        """Parse delivery hour preferences into time string."""
        if time_type == 'start':
            # Find first checked hour
            for hour in range(8, 21):
                if row.get(f'hour_{hour}_{hour+1}'):
                    return f"{hour:02d}:00"
        else:  # end
            # Find last checked hour
            for hour in range(20, 7, -1):
                if row.get(f'hour_{hour}_{hour+1}'):
                    return f"{hour+1:02d}:00"
        
        return None
    
    def _parse_time(self, time_str: str) -> Optional[str]:
        """Parse time string in HH:MM format."""
        if pd.isna(time_str) or not time_str:
            return None
        
        # Ensure it's in HH:MM format
        if ':' in str(time_str):
            return str(time_str)
        
        return None
    
    def _parse_familiar_areas(self, areas_str: str) -> List[str]:
        """Parse comma-separated areas into list."""
        if pd.isna(areas_str) or not areas_str:
            return []
        
        # Split by comma and clean
        areas = [area.strip() for area in str(areas_str).split(',')]
        return [area for area in areas if area]
    
    def _map_order_status(self, legacy_status: str) -> OrderStatus:
        """Map legacy status to new OrderStatus enum."""
        mapping = {
            'pending': OrderStatus.PENDING,
            'confirmed': OrderStatus.CONFIRMED,
            'in_delivery': OrderStatus.IN_DELIVERY,
            'delivered': OrderStatus.DELIVERED,
            'cancelled': OrderStatus.CANCELLED,
            'failed': OrderStatus.FAILED
        }
        return mapping.get(legacy_status, OrderStatus.PENDING)
    
    async def run_migration(self):
        """
        Run the complete migration process.
        """
        logger.info("Starting Lucky Gas data migration...")
        start_time = datetime.now()
        
        async for session in get_async_session():
            try:
                # Initialize products first
                await self.initialize_products(session)
                
                # Migrate in order of dependencies
                await self.migrate_customers(session)
                await self.migrate_drivers(session)
                await self.migrate_vehicles(session)
                await self.migrate_orders(session)
                
                # Generate report
                await self.generate_migration_report()
                
                duration = datetime.now() - start_time
                logger.info(f"Migration completed in {duration}")
                
            except Exception as e:
                logger.error(f"Migration failed: {e}")
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def generate_migration_report(self):
        """Generate detailed migration report."""
        report_path = Path('migration_report.txt')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("Lucky Gas Data Migration Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Migration Date: {datetime.now()}\n")
            f.write(f"Legacy Database: {self.legacy_db_path}\n\n")
            
            # Statistics
            f.write("Migration Statistics:\n")
            f.write("-" * 30 + "\n")
            for table, stats in self.stats.items():
                success_rate = (stats['migrated'] / stats['total'] * 100) if stats['total'] > 0 else 0
                f.write(f"{table.capitalize()}:\n")
                f.write(f"  Total: {stats['total']}\n")
                f.write(f"  Migrated: {stats['migrated']}\n")
                f.write(f"  Failed: {stats['failed']}\n")
                f.write(f"  Success Rate: {success_rate:.2f}%\n\n")
            
            # Encoding conversion report
            f.write("\nEncoding Conversion Report:\n")
            f.write("-" * 30 + "\n")
            conv_report = self.converter.get_conversion_report()
            f.write(f"Total strings processed: {conv_report['statistics']['total_processed']}\n")
            f.write(f"Successful conversions: {conv_report['statistics']['successful']}\n")
            f.write(f"Failed conversions: {conv_report['statistics']['failed']}\n")
            f.write(f"Characters replaced: {conv_report['statistics']['replaced_chars']}\n")
            f.write(f"Overall success rate: {conv_report['success_rate']:.2f}%\n\n")
            
            # Errors
            if self.errors:
                f.write("\nErrors Encountered:\n")
                f.write("-" * 30 + "\n")
                for i, error in enumerate(self.errors[:50]):  # First 50 errors
                    f.write(f"{i+1}. Table: {error['table']}, Record: {error['record']}\n")
                    f.write(f"   Error: {error['error']}\n\n")
                
                if len(self.errors) > 50:
                    f.write(f"... and {len(self.errors) - 50} more errors\n")
        
        logger.info(f"Migration report saved to {report_path}")


@click.command()
@click.option('--legacy-db', required=True, help='Path to legacy SQLite database')
@click.option('--batch-size', default=1000, help='Number of records to process in each batch')
@click.option('--dry-run', is_flag=True, help='Run in dry-run mode (no actual migration)')
def main(legacy_db: str, batch_size: int, dry_run: bool):
    """
    Lucky Gas legacy data migration tool.
    
    Migrates data from SQLite (Big5) to PostgreSQL (UTF-8).
    """
    if dry_run:
        logger.info("Running in DRY-RUN mode - no data will be migrated")
        # TODO: Implement dry-run logic
        return
    
    # Verify legacy database exists
    if not Path(legacy_db).exists():
        logger.error(f"Legacy database not found: {legacy_db}")
        return
    
    # Run migration
    migrator = LegacyDataMigrator(legacy_db, batch_size)
    asyncio.run(migrator.run_migration())


if __name__ == "__main__":
    main()