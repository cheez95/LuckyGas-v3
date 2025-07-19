# Delivery History System Update

## Overview
Updated the delivery history system to support flexible gas products instead of hardcoded cylinder types. This allows the system to adapt to new product types without database schema changes.

## Changes Made

### 1. New Model: DeliveryHistoryItem
Created `/backend/app/models/delivery_history_item.py` with:
- Links to DeliveryHistory and GasProduct models
- Tracks quantity, unit_price, and subtotal
- Supports both cylinder and flow deliveries
- Includes legacy_product_code for backward compatibility

### 2. Updated DeliveryHistory Model
- Added relationship to DeliveryHistoryItem
- Kept old columns (qty_50kg, flow_50kg, etc.) for backward compatibility

### 3. New Schemas
Created `/backend/app/schemas/delivery_history_item.py` with:
- DeliveryHistoryItemBase
- DeliveryHistoryItemCreate
- DeliveryHistoryItemUpdate
- DeliveryHistoryItem

### 4. Updated Schemas
Modified `/backend/app/schemas/delivery_history.py`:
- Added delivery_items field to DeliveryHistory schema

### 5. Import Scripts
Created two new scripts:
- `import_delivery_history_v2.py`: Imports data using the new flexible structure
- `migrate_delivery_history_items.py`: Migrates existing data to the new structure

### 6. Database Migration
Created Alembic migration `004_add_delivery_history_items.py` to create the new table.

## Migration Strategy

### Phase 1: Parallel Operation (Current)
- Old columns remain for backward compatibility
- New delivery_history_items table stores flexible product references
- Both systems work in parallel

### Phase 2: Data Migration
Run the migration script to populate delivery_history_items from existing data:
```bash
cd backend
uv run python app/scripts/migrate_delivery_history_items.py
```

### Phase 3: New Data Import
Use the new import script for future data:
```bash
cd backend
uv run python app/scripts/import_delivery_history_v2.py
```

### Phase 4: API Updates (Future)
- Update API endpoints to use delivery_items relationship
- Deprecate old column-based queries
- Update frontend to use new structure

### Phase 5: Cleanup (Future)
- Remove old columns from DeliveryHistory model
- Update all queries to use DeliveryHistoryItem
- Remove backward compatibility code

## Benefits

1. **Flexibility**: Easy to add new gas products without schema changes
2. **Consistency**: Mirrors the OrderItem pattern
3. **Maintainability**: Single source of truth for product information
4. **Extensibility**: Can add product-specific fields easily

## Testing

Before running in production:
1. Test the migration script on a copy of the database
2. Verify all historical data is correctly migrated
3. Test the new import script with sample data
4. Update API tests to cover new structure

## Notes

- Unit prices in historical data default to 100.0 since we don't have historical pricing
- The legacy_product_code field helps trace items back to original columns
- Flow deliveries store actual quantity in flow_quantity field
- Cylinder deliveries use the quantity field for number of cylinders