"""
Incremental sync service for Lucky Gas data migration
Handles real-time synchronization between legacy and new systems
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as redis
import sqlite3
import pandas as pd
import json

from app.utils.encoding_converter import Big5ToUTF8Converter
from app.core.database import get_async_session
from app.models import Customer, User, Order, OrderItem, GasProduct, Vehicle
from app.models.order import OrderStatus, PaymentStatus
from app.models.user import UserRole

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
        sync_interval_minutes: int = 5,
        batch_size: int = 100,
    ):
        self.legacy_db_path = legacy_db_path
        self.redis_url = redis_url
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        self.batch_size = batch_size
        self.converter = Big5ToUTF8Converter()
        self.redis: Optional[redis.Redis] = None
        self.is_running = False

        # Table sync configuration
        self.sync_config = {
            "clients": {
                "legacy_to_new": True,
                "new_to_legacy": False,  # One-way for customers
                "id_mapping_key": "sync:id_map:customers",
                "timestamp_key": "sync:timestamp:clients",
                "text_fields": [
                    "client_code",
                    "invoice_title",
                    "short_name",
                    "address",
                    "name",
                    "contact_person",
                    "district",
                    "notes",
                    "area",
                ],
                "conflict_resolution": "newest_wins",
                "new_model": Customer,
                "sync_method": self.sync_customer_record,
            },
            "deliveries": {
                "legacy_to_new": True,
                "new_to_legacy": True,  # Bidirectional for orders
                "id_mapping_key": "sync:id_map:orders",
                "timestamp_key": "sync:timestamp:deliveries",
                "text_fields": ["notes"],
                "conflict_resolution": "newest_wins",
                "new_model": Order,
                "sync_method": self.sync_order_record,
            },
            "drivers": {
                "legacy_to_new": True,
                "new_to_legacy": False,
                "id_mapping_key": "sync:id_map:drivers",
                "timestamp_key": "sync:timestamp:drivers",
                "text_fields": ["name", "familiar_areas"],
                "conflict_resolution": "newest_wins",
                "new_model": User,
                "sync_method": self.sync_driver_record,
            },
            "vehicles": {
                "legacy_to_new": True,
                "new_to_legacy": False,
                "id_mapping_key": "sync:id_map:vehicles",
                "timestamp_key": "sync:timestamp:vehicles",
                "text_fields": ["plate_number", "vehicle_type"],
                "conflict_resolution": "newest_wins",
                "new_model": Vehicle,
                "sync_method": self.sync_vehicle_record,
            },
        }

        # Sync statistics
        self.stats = {
            "last_sync": None,
            "records_synced": 0,
            "conflicts_resolved": 0,
            "errors": 0,
            "cycles_completed": 0,
        }

    async def initialize(self):
        """Initialize Redis connection and sync state."""
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis.ping()
        logger.info("Incremental sync service initialized")

    async def cleanup(self):
        """Clean up resources."""
        if self.redis:
            await self.redis.close()

    async def start_sync_loop(self):
        """Start the continuous sync loop."""
        self.is_running = True
        logger.info(f"Starting sync loop with {self.sync_interval.seconds}s interval")

        while self.is_running:
            try:
                await self.run_sync_cycle()
                await asyncio.sleep(self.sync_interval.seconds)
            except asyncio.CancelledError:
                logger.info("Sync loop cancelled")
                break
            except Exception as e:
                logger.error(f"Sync cycle failed: {e}", exc_info=True)
                self.stats["errors"] += 1
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def stop_sync_loop(self):
        """Stop the sync loop gracefully."""
        self.is_running = False
        await self.cleanup()

    async def run_sync_cycle(self):
        """Run a single sync cycle for all configured tables."""
        logger.info("Starting sync cycle")
        cycle_start = datetime.now()

        async for session in get_async_session():
            try:
                # Process each table
                for table_name, config in self.sync_config.items():
                    if config["legacy_to_new"]:
                        await self.sync_legacy_to_new(table_name, config, session)

                    if config["new_to_legacy"]:
                        await self.sync_new_to_legacy(table_name, config, session)

                await session.commit()

                # Update stats
                self.stats["last_sync"] = datetime.now()
                self.stats["cycles_completed"] += 1

                # Save stats to Redis
                await self.save_sync_stats()

                duration = datetime.now() - cycle_start
                logger.info(
                    f"Sync cycle completed in {duration.seconds}s. "
                    f"Synced {self.stats['records_synced']} records"
                )

            except Exception as e:
                await session.rollback()
                logger.error(f"Sync cycle error: {e}")
                raise
            finally:
                await session.close()

    async def sync_legacy_to_new(
        self, table_name: str, config: Dict[str, Any], session: AsyncSession
    ):
        """Sync changes from legacy to new system."""
        # Get last sync timestamp
        last_sync = await self.get_last_sync_time(config["timestamp_key"])

        # Fetch changed records from legacy
        legacy_changes = self.fetch_legacy_changes(table_name, last_sync)

        if legacy_changes.empty:
            logger.debug(f"No changes found in legacy {table_name}")
            return

        logger.info(f"Found {len(legacy_changes)} changes in legacy {table_name}")

        # Convert encoding
        legacy_changes = self.converter.convert_dataframe(
            legacy_changes, columns=config["text_fields"]
        )

        # Process in batches
        for start_idx in range(0, len(legacy_changes), self.batch_size):
            batch = legacy_changes.iloc[start_idx : start_idx + self.batch_size]

            for _, record in batch.iterrows():
                try:
                    await config["sync_method"](record, config, session)
                    self.stats["records_synced"] += 1
                except Exception as e:
                    logger.error(
                        f"Failed to sync {table_name} record {record.get('id')}: {e}"
                    )
                    self.stats["errors"] += 1

            # Commit batch
            await session.commit()

        # Update sync timestamp
        if not legacy_changes.empty:
            max_timestamp = legacy_changes["updated_at"].max()
            await self.set_last_sync_time(
                config["timestamp_key"], pd.to_datetime(max_timestamp)
            )

    async def sync_new_to_legacy(
        self, table_name: str, config: Dict[str, Any], session: AsyncSession
    ):
        """Sync changes from new system to legacy (for bidirectional tables)."""
        if table_name != "deliveries":
            return  # Currently only orders/deliveries are bidirectional

        # Get last sync timestamp
        last_sync = await self.get_last_sync_time(f"{config['timestamp_key']}:reverse")

        # Fetch changed orders from new system
        stmt = select(Order).where(Order.updated_at > last_sync).limit(self.batch_size)
        result = await session.execute(stmt)
        orders = result.scalars().all()

        if not orders:
            return

        logger.info(f"Found {len(orders)} changes in new system for {table_name}")

        # Update legacy system
        conn = sqlite3.connect(self.legacy_db_path)
        cursor = conn.cursor()

        try:
            for order in orders:
                # Get legacy ID from mapping
                legacy_id = await self.get_reverse_id_mapping(
                    config["id_mapping_key"], order.id
                )

                if legacy_id:
                    # Update existing legacy record
                    cursor.execute(
                        """
                        UPDATE deliveries 
                        SET status = ?, actual_delivery_time = ?, notes = ?, updated_at = ?
                        WHERE id = ?
                    """,
                        (
                            order.status.value,
                            (
                                order.delivered_at.isoformat()
                                if order.delivered_at
                                else None
                            ),
                            order.delivery_notes,
                            datetime.now().isoformat(),
                            legacy_id,
                        ),
                    )

            conn.commit()

            # Update reverse sync timestamp
            max_timestamp = max(order.updated_at for order in orders)
            await self.set_last_sync_time(
                f"{config['timestamp_key']}:reverse", max_timestamp
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to sync to legacy: {e}")
            raise
        finally:
            conn.close()

    def fetch_legacy_changes(
        self, table_name: str, last_sync: datetime
    ) -> pd.DataFrame:
        """Fetch changed records from legacy database."""
        conn = sqlite3.connect(self.legacy_db_path)

        # Check if table has updated_at column
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {col[1] for col in cursor.fetchall()}

        if "updated_at" in columns:
            query = f"""
            SELECT * FROM {table_name}
            WHERE updated_at > ?
            ORDER BY updated_at ASC
            LIMIT ?
            """
            params = (last_sync.isoformat(), self.batch_size)
        else:
            # For tables without updated_at, use created_at or id
            if "created_at" in columns:
                query = f"""
                SELECT * FROM {table_name}
                WHERE created_at > ?
                ORDER BY created_at ASC
                LIMIT ?
                """
                params = (last_sync.isoformat(), self.batch_size)
            else:
                # Fallback: get all records (for initial sync)
                query = f"SELECT * FROM {table_name} LIMIT ?"
                params = (self.batch_size,)

        df = pd.read_sql_query(query, conn, params=params)

        # Add updated_at if missing (for tracking)
        if "updated_at" not in df.columns:
            df["updated_at"] = datetime.now()

        conn.close()
        return df

    async def sync_customer_record(
        self, record: pd.Series, config: Dict[str, Any], session: AsyncSession
    ):
        """Sync a customer record."""
        # Get ID mapping
        legacy_id = record["id"]
        new_id = await self.get_id_mapping(config["id_mapping_key"], legacy_id)

        if new_id:
            # Check if customer exists
            customer = await session.get(Customer, new_id)
            if customer:
                # Check for conflicts using updated_at
                if hasattr(customer, "updated_at") and customer.updated_at:
                    record_updated = pd.to_datetime(
                        record.get("updated_at", datetime.min)
                    )
                    if customer.updated_at > record_updated:
                        logger.debug(
                            f"Skipping customer {record['client_code']} - newer version exists"
                        )
                        self.stats["conflicts_resolved"] += 1
                        return

                # Update existing customer
                customer.name = record.get("invoice_title") or record.get("short_name")
                customer.short_name = record.get("short_name")
                customer.address = record.get("address")
                customer.phone = self._extract_phone(record.get("contact_person", ""))
                customer.contact_person = record.get("contact_person")
                customer.notes = record.get("notes")
                customer.is_active = bool(record.get("is_active", True))
                customer.is_terminated = bool(record.get("is_terminated", False))
                customer.updated_at = datetime.now()

                logger.debug(f"Updated customer {customer.customer_code}")
                return

        # Check if customer with this code already exists
        stmt = select(Customer).where(Customer.customer_code == record["client_code"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Store mapping for existing customer
            await self.set_id_mapping(config["id_mapping_key"], legacy_id, existing.id)
            return

        # Create new customer
        customer = Customer(
            customer_code=record["client_code"],
            name=record.get("invoice_title") or record.get("short_name"),
            short_name=record.get("short_name"),
            address=record.get("address"),
            phone=self._extract_phone(record.get("contact_person", "")),
            contact_person=record.get("contact_person"),
            tax_id=record.get("tax_id") if pd.notna(record.get("tax_id")) else None,
            customer_type="corporate" if record.get("is_corporate") else "residential",
            district=record.get("district"),
            area=record.get("area"),
            latitude=(
                float(record["latitude"]) if pd.notna(record.get("latitude")) else None
            ),
            longitude=(
                float(record["longitude"])
                if pd.notna(record.get("longitude"))
                else None
            ),
            is_active=bool(record.get("is_active", True)),
            is_terminated=bool(record.get("is_terminated", False)),
            payment_method=self._map_payment_method(record.get("payment_method")),
            pricing_type=record.get("pricing_method", "standard"),
            delivery_time_preference=record.get("delivery_time_preference"),
            needs_same_day_delivery=bool(record.get("needs_same_day_delivery")),
            has_flow_meter=bool(record.get("has_flow_meter")),
            has_switch=bool(record.get("has_switch")),
            cylinder_inventory={
                "50kg": int(record.get("cylinder_50kg", 0)),
                "20kg": int(record.get("cylinder_20kg", 0)),
                "16kg": int(record.get("cylinder_16kg", 0)),
                "10kg": int(record.get("cylinder_10kg", 0)),
                "4kg": int(record.get("cylinder_4kg", 0)),
            },
            monthly_delivery_volume=(
                float(record.get("monthly_delivery_volume", 0))
                if pd.notna(record.get("monthly_delivery_volume"))
                else None
            ),
            daily_usage_avg=(
                float(record.get("daily_usage_avg", 0))
                if pd.notna(record.get("daily_usage_avg"))
                else None
            ),
            notes=record.get("notes"),
            created_at=pd.to_datetime(record.get("created_at", datetime.now())),
            updated_at=pd.to_datetime(record.get("updated_at", datetime.now())),
        )

        session.add(customer)
        await session.flush()

        # Store ID mapping
        await self.set_id_mapping(config["id_mapping_key"], legacy_id, customer.id)
        logger.debug(f"Created new customer {customer.customer_code}")

    async def sync_order_record(
        self, record: pd.Series, config: Dict[str, Any], session: AsyncSession
    ):
        """Sync an order/delivery record."""
        # Similar implementation to sync_customer_record
        # but for orders with order items
        pass

    async def sync_driver_record(
        self, record: pd.Series, config: Dict[str, Any], session: AsyncSession
    ):
        """Sync a driver record as user."""
        legacy_id = record["id"]
        new_id = await self.get_id_mapping(config["id_mapping_key"], legacy_id)

        email = f"{record['employee_id']}@luckygas.tw"

        if new_id:
            # Update existing driver
            user = await session.get(User, new_id)
            if user:
                user.full_name = record["name"]
                user.phone = record.get("phone")
                user.is_active = bool(record.get("is_active", True))
                user.driver_license_type = record.get("license_type")
                user.driver_experience_years = (
                    int(record.get("experience_years", 0))
                    if pd.notna(record.get("experience_years"))
                    else None
                )
                user.is_available = bool(record.get("is_available", True))
                user.updated_at = datetime.now()
                return

        # Check if user with this email exists
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            await self.set_id_mapping(config["id_mapping_key"], legacy_id, existing.id)
            return

        # Create new driver user
        user = User(
            email=email,
            full_name=record["name"],
            phone=record.get("phone"),
            employee_id=record["employee_id"],
            role=UserRole.DRIVER,
            is_active=bool(record.get("is_active", True)),
            driver_license_type=record.get("license_type"),
            driver_experience_years=(
                int(record.get("experience_years", 0))
                if pd.notna(record.get("experience_years"))
                else None
            ),
            driver_familiar_areas=self._parse_familiar_areas(
                record.get("familiar_areas")
            ),
            is_available=bool(record.get("is_available", True)),
            created_at=pd.to_datetime(record.get("created_at", datetime.now())),
            updated_at=pd.to_datetime(record.get("updated_at", datetime.now())),
        )

        # Set temporary password
        user.set_password(f"LuckyGas@{record['employee_id']}")

        session.add(user)
        await session.flush()

        await self.set_id_mapping(config["id_mapping_key"], legacy_id, user.id)
        logger.debug(f"Created new driver user {user.email}")

    async def sync_vehicle_record(
        self, record: pd.Series, config: Dict[str, Any], session: AsyncSession
    ):
        """Sync a vehicle record."""
        legacy_id = record["id"]
        new_id = await self.get_id_mapping(config["id_mapping_key"], legacy_id)

        if new_id:
            vehicle = await session.get(Vehicle, new_id)
            if vehicle:
                vehicle.is_active = bool(record.get("is_active", True))
                vehicle.is_available = bool(record.get("is_available", True))
                vehicle.updated_at = datetime.now()
                return

        # Check if vehicle with this plate exists
        stmt = select(Vehicle).where(Vehicle.plate_number == record["plate_number"])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            await self.set_id_mapping(config["id_mapping_key"], legacy_id, existing.id)
            return

        # Map driver ID if assigned
        driver_id = None
        if pd.notna(record.get("driver_id")):
            driver_id = await self.get_id_mapping(
                self.sync_config["drivers"]["id_mapping_key"], int(record["driver_id"])
            )

        # Create new vehicle
        vehicle = Vehicle(
            plate_number=record["plate_number"],
            vehicle_type=record["vehicle_type"],
            is_active=bool(record.get("is_active", True)),
            is_available=bool(record.get("is_available", True)),
            assigned_driver_id=driver_id,
            capacity_50kg=int(record.get("max_cylinders_50kg", 0)),
            capacity_20kg=int(record.get("max_cylinders_20kg", 0)),
            capacity_16kg=int(record.get("max_cylinders_16kg", 0)),
            capacity_10kg=int(record.get("max_cylinders_10kg", 0)),
            capacity_4kg=int(record.get("max_cylinders_4kg", 0)),
            last_maintenance_date=(
                pd.to_datetime(record.get("last_maintenance"))
                if pd.notna(record.get("last_maintenance"))
                else None
            ),
            next_maintenance_date=(
                pd.to_datetime(record.get("next_maintenance"))
                if pd.notna(record.get("next_maintenance"))
                else None
            ),
            created_at=pd.to_datetime(record.get("created_at", datetime.now())),
            updated_at=pd.to_datetime(record.get("updated_at", datetime.now())),
        )

        session.add(vehicle)
        await session.flush()

        await self.set_id_mapping(config["id_mapping_key"], legacy_id, vehicle.id)
        logger.debug(f"Created new vehicle {vehicle.plate_number}")

    # Redis helper methods

    async def get_last_sync_time(self, key: str) -> datetime:
        """Get last sync timestamp from Redis."""
        timestamp = await self.redis.get(key)
        if timestamp:
            return datetime.fromisoformat(timestamp)
        return datetime(2000, 1, 1)  # Default to old date for initial sync

    async def set_last_sync_time(self, key: str, timestamp: datetime):
        """Set last sync timestamp in Redis."""
        await self.redis.set(key, timestamp.isoformat())

    async def get_id_mapping(self, key: str, legacy_id: int) -> Optional[int]:
        """Get new system ID for a legacy ID."""
        new_id = await self.redis.hget(key, str(legacy_id))
        return int(new_id) if new_id else None

    async def get_reverse_id_mapping(self, key: str, new_id: int) -> Optional[int]:
        """Get legacy ID for a new system ID (for reverse sync)."""
        # Store reverse mappings with :reverse suffix
        reverse_key = f"{key}:reverse"
        legacy_id = await self.redis.hget(reverse_key, str(new_id))
        return int(legacy_id) if legacy_id else None

    async def set_id_mapping(self, key: str, legacy_id: int, new_id: int):
        """Store ID mapping between systems (bidirectional)."""
        # Store forward mapping
        await self.redis.hset(key, str(legacy_id), str(new_id))
        # Store reverse mapping
        reverse_key = f"{key}:reverse"
        await self.redis.hset(reverse_key, str(new_id), str(legacy_id))

    async def save_sync_stats(self):
        """Save sync statistics to Redis."""
        stats_key = "sync:stats"
        await self.redis.set(stats_key, json.dumps(self.stats, default=str))

    async def get_sync_stats(self) -> Dict[str, Any]:
        """Get sync statistics from Redis."""
        stats_key = "sync:stats"
        stats_json = await self.redis.get(stats_key)
        if stats_json:
            return json.loads(stats_json)
        return self.stats

    # Helper methods

    def _extract_phone(self, contact_info: str) -> Optional[str]:
        """Extract phone number from contact info."""
        if not contact_info:
            return None

        import re

        phone_pattern = r"(09\d{2}[-\s]?\d{3}[-\s]?\d{3}|0[2-8][-\s]?\d{4}[-\s]?\d{4})"
        match = re.search(phone_pattern, contact_info)
        return match.group(1).replace(" ", "").replace("-", "") if match else None

    def _map_payment_method(self, legacy_method: str) -> str:
        """Map legacy payment method to new enum."""
        if pd.isna(legacy_method):
            return "cash"

        mapping = {
            "cash": "cash",
            "credit": "monthly",
            "transfer": "transfer",
            "現金": "cash",
            "月結": "monthly",
            "轉帳": "transfer",
        }
        return mapping.get(str(legacy_method).lower(), "cash")

    def _parse_familiar_areas(self, areas_str: str) -> List[str]:
        """Parse comma-separated areas into list."""
        if pd.isna(areas_str) or not areas_str:
            return []

        areas = [area.strip() for area in str(areas_str).split(",")]
        return [area for area in areas if area]


# Conflict resolution strategies
class ConflictResolver:
    """Handles conflicts during bidirectional sync."""

    @staticmethod
    def newest_wins(legacy_record: Dict, new_record: Any) -> str:
        """Resolution: Keep the record with the latest timestamp."""
        legacy_time = pd.to_datetime(legacy_record.get("updated_at", datetime.min))
        new_time = getattr(new_record, "updated_at", datetime.min)

        return "legacy" if legacy_time > new_time else "new"

    @staticmethod
    def legacy_wins(legacy_record: Dict, new_record: Any) -> str:
        """Resolution: Always prefer legacy system data."""
        return "legacy"

    @staticmethod
    def new_wins(legacy_record: Dict, new_record: Any) -> str:
        """Resolution: Always prefer new system data."""
        return "new"
