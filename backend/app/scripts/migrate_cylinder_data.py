#!/usr/bin/env python3
"""
Migration script to convert existing customer cylinder data to the new flexible product system.

This script:
1. Maps old cylinder columns to appropriate GasProduct IDs
2. Creates CustomerInventory records for each customer's cylinders
3. Handles special cases like haoyun (好運) and ying (營) cylinders
4. Includes validation and rollback capability
5. Provides progress tracking and error handling
6. Supports dry-run mode to preview changes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from typing import Dict, List, Tuple, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import argparse
from tqdm import tqdm
from datetime import datetime

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.customer import Customer
from app.models.gas_product import GasProduct, DeliveryMethod, ProductAttribute
from app.models.customer_inventory import CustomerInventory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CylinderDataMigrator:
    """Handles migration of cylinder data from old customer model to new inventory system."""
    
    # Mapping of old column names to product specifications
    CYLINDER_MAPPING = {
        'cylinders_50kg': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 50,
            'attribute': ProductAttribute.REGULAR
        },
        'cylinders_20kg': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 20,
            'attribute': ProductAttribute.REGULAR
        },
        'cylinders_16kg': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 16,
            'attribute': ProductAttribute.REGULAR
        },
        'cylinders_10kg': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 10,
            'attribute': ProductAttribute.REGULAR
        },
        'cylinders_4kg': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 4,
            'attribute': ProductAttribute.REGULAR
        },
        'cylinders_ying20': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 20,
            'attribute': ProductAttribute.PINGAN  # 營 cylinders map to PINGAN
        },
        'cylinders_ying16': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 16,
            'attribute': ProductAttribute.PINGAN  # 營 cylinders map to PINGAN
        },
        'cylinders_haoyun20': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 20,
            'attribute': ProductAttribute.HAOYUN
        },
        'cylinders_haoyun16': {
            'delivery_method': DeliveryMethod.CYLINDER,
            'size_kg': 16,
            'attribute': ProductAttribute.HAOYUN
        }
    }
    
    def __init__(self, db: Session, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.product_cache: Dict[str, Optional[GasProduct]] = {}
        self.migration_stats = {
            'customers_processed': 0,
            'inventory_created': 0,
            'inventory_updated': 0,
            'errors': 0,
            'skipped': 0
        }
        self.rollback_data: List[Dict] = []
        
    def get_or_create_product(self, specs: Dict) -> Optional[GasProduct]:
        """Get existing product or create if not exists."""
        cache_key = f"{specs['delivery_method']}_{specs['size_kg']}_{specs['attribute']}"
        
        if cache_key in self.product_cache:
            return self.product_cache[cache_key]
        
        product = self.db.query(GasProduct).filter(
            GasProduct.delivery_method == specs['delivery_method'],
            GasProduct.size_kg == specs['size_kg'],
            GasProduct.attribute == specs['attribute']
        ).first()
        
        if not product and not self.dry_run:
            # Create the product if it doesn't exist
            product = GasProduct(
                delivery_method=specs['delivery_method'],
                size_kg=specs['size_kg'],
                attribute=specs['attribute'],
                sku=self._generate_sku(specs),
                name_zh=self._generate_name_zh(specs),
                unit_price=0.0,  # Will need to be set manually
                is_active=True,
                is_available=True
            )
            self.db.add(product)
            self.db.flush()
            logger.info(f"Created new product: {product.sku}")
        
        self.product_cache[cache_key] = product
        return product
    
    def _generate_sku(self, specs: Dict) -> str:
        """Generate SKU for product."""
        method_code = "C" if specs['delivery_method'] == DeliveryMethod.CYLINDER else "F"
        attr_code = {
            ProductAttribute.REGULAR: "R",
            ProductAttribute.HAOYUN: "H",
            ProductAttribute.PINGAN: "P"
        }.get(specs['attribute'], "R")
        
        return f"GAS-{method_code}{specs['size_kg']:02d}-{attr_code}"
    
    def _generate_name_zh(self, specs: Dict) -> str:
        """Generate Traditional Chinese name for product."""
        method_name = "桶裝" if specs['delivery_method'] == DeliveryMethod.CYLINDER else "流量"
        attr_name = {
            ProductAttribute.REGULAR: "",
            ProductAttribute.HAOYUN: "好運",
            ProductAttribute.PINGAN: "瓶安"
        }.get(specs['attribute'], "")
        
        if attr_name:
            return f"{attr_name}{specs['size_kg']}公斤{method_name}"
        else:
            return f"{specs['size_kg']}公斤{method_name}"
    
    def migrate_customer(self, customer: Customer) -> Tuple[int, int]:
        """Migrate cylinder data for a single customer."""
        created_count = 0
        updated_count = 0
        
        try:
            for column_name, product_specs in self.CYLINDER_MAPPING.items():
                cylinder_count = getattr(customer, column_name, 0) or 0
                
                if cylinder_count <= 0:
                    continue
                
                # Get or create the product
                product = self.get_or_create_product(product_specs)
                if not product:
                    logger.warning(f"Could not get/create product for {column_name}")
                    continue
                
                # Check if inventory record already exists
                existing_inventory = self.db.query(CustomerInventory).filter(
                    CustomerInventory.customer_id == customer.id,
                    CustomerInventory.gas_product_id == product.id
                ).first()
                
                if existing_inventory:
                    # Update existing record
                    if not self.dry_run:
                        # Store rollback data
                        self.rollback_data.append({
                            'action': 'update',
                            'id': existing_inventory.id,
                            'old_quantity': existing_inventory.quantity_total,
                            'old_owned': existing_inventory.quantity_owned,
                            'old_rented': existing_inventory.quantity_rented
                        })
                        
                        existing_inventory.quantity_total = cylinder_count
                        existing_inventory.quantity_owned = cylinder_count  # Assume all are owned
                        existing_inventory.quantity_rented = 0
                        existing_inventory.is_active = True
                    
                    logger.debug(f"Updated inventory for customer {customer.customer_code}: "
                               f"{product.sku} = {cylinder_count}")
                    updated_count += 1
                else:
                    # Create new inventory record
                    if not self.dry_run:
                        new_inventory = CustomerInventory(
                            customer_id=customer.id,
                            gas_product_id=product.id,
                            quantity_owned=cylinder_count,  # Assume all cylinders are owned
                            quantity_rented=0,
                            quantity_total=cylinder_count,
                            is_active=True
                        )
                        self.db.add(new_inventory)
                        
                        # Store rollback data
                        self.rollback_data.append({
                            'action': 'create',
                            'customer_id': customer.id,
                            'gas_product_id': product.id
                        })
                    
                    logger.debug(f"Created inventory for customer {customer.customer_code}: "
                               f"{product.sku} = {cylinder_count}")
                    created_count += 1
            
            return created_count, updated_count
            
        except Exception as e:
            logger.error(f"Error migrating customer {customer.customer_code}: {str(e)}")
            self.migration_stats['errors'] += 1
            raise
    
    def validate_migration(self) -> bool:
        """Validate the migration by checking data consistency."""
        logger.info("Validating migration...")
        
        # Check that all customers with cylinder data have inventory records
        customers_with_cylinders = self.db.query(Customer).filter(
            (Customer.cylinders_50kg > 0) |
            (Customer.cylinders_20kg > 0) |
            (Customer.cylinders_16kg > 0) |
            (Customer.cylinders_10kg > 0) |
            (Customer.cylinders_4kg > 0) |
            (Customer.cylinders_ying20 > 0) |
            (Customer.cylinders_ying16 > 0) |
            (Customer.cylinders_haoyun20 > 0) |
            (Customer.cylinders_haoyun16 > 0)
        ).count()
        
        customers_with_inventory = self.db.query(Customer).join(
            CustomerInventory
        ).distinct().count()
        
        logger.info(f"Customers with cylinder data: {customers_with_cylinders}")
        logger.info(f"Customers with inventory records: {customers_with_inventory}")
        
        if customers_with_cylinders > customers_with_inventory:
            logger.warning(f"Some customers may not have been migrated: "
                         f"{customers_with_cylinders - customers_with_inventory} missing")
        
        return True
    
    def rollback(self):
        """Rollback the migration using stored rollback data."""
        logger.info("Rolling back migration...")
        
        for item in reversed(self.rollback_data):
            try:
                if item['action'] == 'create':
                    # Delete created records
                    self.db.query(CustomerInventory).filter(
                        CustomerInventory.customer_id == item['customer_id'],
                        CustomerInventory.gas_product_id == item['gas_product_id']
                    ).delete()
                elif item['action'] == 'update':
                    # Restore original values
                    inventory = self.db.query(CustomerInventory).filter(
                        CustomerInventory.id == item['id']
                    ).first()
                    if inventory:
                        inventory.quantity_total = item['old_quantity']
                        inventory.quantity_owned = item['old_owned']
                        inventory.quantity_rented = item['old_rented']
            except Exception as e:
                logger.error(f"Error during rollback: {str(e)}")
        
        self.db.commit()
        logger.info("Rollback completed")
    
    def run(self):
        """Execute the migration."""
        logger.info(f"Starting cylinder data migration (dry_run={self.dry_run})")
        
        try:
            # Get all customers
            customers = self.db.query(Customer).all()
            total_customers = len(customers)
            logger.info(f"Found {total_customers} customers to process")
            
            # Process each customer with progress bar
            with tqdm(total=total_customers, desc="Migrating customers") as pbar:
                for customer in customers:
                    created, updated = self.migrate_customer(customer)
                    self.migration_stats['customers_processed'] += 1
                    self.migration_stats['inventory_created'] += created
                    self.migration_stats['inventory_updated'] += updated
                    pbar.update(1)
            
            if not self.dry_run:
                # Commit the transaction
                self.db.commit()
                logger.info("Migration committed successfully")
                
                # Validate the migration
                self.validate_migration()
            else:
                logger.info("Dry run completed - no changes were made")
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            if not self.dry_run:
                self.db.rollback()
                logger.info("Transaction rolled back")
            raise
    
    def print_summary(self):
        """Print migration summary."""
        logger.info("\n" + "="*50)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*50)
        logger.info(f"Customers processed: {self.migration_stats['customers_processed']}")
        logger.info(f"Inventory records created: {self.migration_stats['inventory_created']}")
        logger.info(f"Inventory records updated: {self.migration_stats['inventory_updated']}")
        logger.info(f"Errors encountered: {self.migration_stats['errors']}")
        logger.info(f"Records skipped: {self.migration_stats['skipped']}")
        logger.info("="*50)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate customer cylinder data to new inventory system"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback a previous migration"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create database session
    db = SessionLocal()
    
    try:
        migrator = CylinderDataMigrator(db, dry_run=args.dry_run)
        
        if args.rollback:
            logger.warning("Rollback functionality requires stored rollback data from a previous run")
            response = input("Are you sure you want to rollback? (yes/no): ")
            if response.lower() == 'yes':
                migrator.rollback()
        else:
            migrator.run()
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()