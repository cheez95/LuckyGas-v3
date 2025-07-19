# Customer Cylinder Data Migration Guide

## Overview

This guide documents the migration process for converting existing customer cylinder data from the old hardcoded column system to the new flexible product inventory system.

## Background

### Old System
The Customer model had hardcoded columns for each cylinder type:
- `cylinders_50kg`, `cylinders_20kg`, `cylinders_16kg`, `cylinders_10kg`, `cylinders_4kg`
- `cylinders_ying20`, `cylinders_ying16` (營 cylinders)
- `cylinders_haoyun20`, `cylinders_haoyun16` (好運 cylinders)

### New System
The new system uses:
- `GasProduct` model with flexible combinations of:
  - Delivery method (CYLINDER/FLOW)
  - Size (4/10/16/20/50 kg)
  - Attribute (REGULAR/HAOYUN/PINGAN)
- `CustomerInventory` model linking customers to products with quantities

## Migration Script

### Usage

```bash
# Navigate to backend directory
cd /path/to/LuckyGas-v3/backend

# Dry run - preview changes without making them
python -m app.scripts.migrate_cylinder_data --dry-run

# Verbose dry run - see detailed logs
python -m app.scripts.migrate_cylinder_data --dry-run --verbose

# Execute the actual migration
python -m app.scripts.migrate_cylinder_data

# Rollback (if needed)
python -m app.scripts.migrate_cylinder_data --rollback
```

### Command-line Options

- `--dry-run`: Preview changes without modifying database
- `--verbose` or `-v`: Enable detailed logging
- `--rollback`: Rollback a previous migration (requires rollback data)

## Mapping Logic

| Old Column | Product Specifications |
|------------|----------------------|
| `cylinders_50kg` | CYLINDER, 50kg, REGULAR |
| `cylinders_20kg` | CYLINDER, 20kg, REGULAR |
| `cylinders_16kg` | CYLINDER, 16kg, REGULAR |
| `cylinders_10kg` | CYLINDER, 10kg, REGULAR |
| `cylinders_4kg` | CYLINDER, 4kg, REGULAR |
| `cylinders_ying20` | CYLINDER, 20kg, PINGAN |
| `cylinders_ying16` | CYLINDER, 16kg, PINGAN |
| `cylinders_haoyun20` | CYLINDER, 20kg, HAOYUN |
| `cylinders_haoyun16` | CYLINDER, 16kg, HAOYUN |

## Migration Process

1. **Product Creation/Lookup**
   - The script checks if required GasProduct records exist
   - Creates missing products automatically (with 0 unit price)
   - Caches products for performance

2. **Inventory Migration**
   - For each customer with cylinder data:
     - Creates CustomerInventory records for each cylinder type
     - Assumes all cylinders are owned (not rented)
     - Sets quantity_total = quantity_owned

3. **Validation**
   - Compares customers with cylinder data vs. customers with inventory records
   - Reports any discrepancies

4. **Logging**
   - Creates timestamped log file: `migration_YYYYMMDD_HHMMSS.log`
   - Logs all actions and errors
   - Provides summary statistics

## Safety Features

1. **Dry Run Mode**
   - Test the migration without making changes
   - Shows what would be created/updated
   - Validates data integrity

2. **Idempotency**
   - Safe to run multiple times
   - Updates existing inventory records if found
   - Won't create duplicates

3. **Transaction Management**
   - All changes in single transaction
   - Automatic rollback on error
   - Consistent state guaranteed

4. **Rollback Capability**
   - Stores rollback data during migration
   - Can undo changes if needed
   - Preserves data integrity

## Post-Migration Tasks

1. **Set Product Prices**
   ```sql
   -- Update unit prices for all products
   UPDATE gas_products 
   SET unit_price = <price> 
   WHERE sku = 'GAS-C20-R';  -- Example for 20kg regular cylinder
   ```

2. **Verify Data**
   ```sql
   -- Check migration results
   SELECT c.customer_code, c.short_name, 
          gp.sku, gp.name_zh, ci.quantity_total
   FROM customers c
   JOIN customer_inventory ci ON ci.customer_id = c.id
   JOIN gas_products gp ON gp.id = ci.gas_product_id
   WHERE ci.quantity_total > 0
   ORDER BY c.customer_code, gp.size_kg DESC;
   ```

3. **Update Rental vs Owned Status**
   ```sql
   -- If you know which cylinders are rented
   UPDATE customer_inventory
   SET quantity_rented = <rented_count>,
       quantity_owned = quantity_total - <rented_count>
   WHERE customer_id = <customer_id> 
     AND gas_product_id = <product_id>;
   ```

4. **Clean Up Old Columns** (After verification)
   ```sql
   -- Remove old cylinder columns from customers table
   -- WARNING: Only do this after thorough testing!
   ALTER TABLE customers 
   DROP COLUMN cylinders_50kg,
   DROP COLUMN cylinders_20kg,
   DROP COLUMN cylinders_16kg,
   DROP COLUMN cylinders_10kg,
   DROP COLUMN cylinders_4kg,
   DROP COLUMN cylinders_ying20,
   DROP COLUMN cylinders_ying16,
   DROP COLUMN cylinders_haoyun20,
   DROP COLUMN cylinders_haoyun16;
   ```

## Troubleshooting

### Common Issues

1. **"Product not found" errors**
   - Ensure seed_gas_products.py was run first
   - Check product attribute mappings

2. **Duplicate key violations**
   - CustomerInventory already exists
   - Script will update existing records

3. **Memory issues with large datasets**
   - Process in batches by modifying the script
   - Use pagination in the customer query

### Validation Queries

```sql
-- Count customers with old cylinder data
SELECT COUNT(*) FROM customers
WHERE cylinders_50kg > 0 
   OR cylinders_20kg > 0 
   OR cylinders_16kg > 0 
   OR cylinders_10kg > 0 
   OR cylinders_4kg > 0
   OR cylinders_ying20 > 0
   OR cylinders_ying16 > 0
   OR cylinders_haoyun20 > 0
   OR cylinders_haoyun16 > 0;

-- Count customers with new inventory records
SELECT COUNT(DISTINCT customer_id) 
FROM customer_inventory 
WHERE quantity_total > 0;

-- Check for missing products
SELECT DISTINCT 
  delivery_method, size_kg, attribute
FROM gas_products
ORDER BY delivery_method, size_kg, attribute;
```

## Notes

- The migration assumes all existing cylinders are customer-owned
- Rental vs owned status will need manual adjustment
- Product prices must be set after migration
- Flow meter data is not migrated (no old system equivalent)
- The script is designed to be run once but is safe to run multiple times