# Lucky Gas Data Migration Field Mapping Document

This document provides comprehensive field-by-field mapping between the legacy system (SQLite/ASP.NET) and the new system (PostgreSQL/React+FastAPI) for all 7 remaining modules.

## Overview

- **Source Encoding**: Big5 (Traditional Chinese)
- **Target Encoding**: UTF-8
- **Database**: SQLite → PostgreSQL
- **Data Types**: Various conversions required
- **Special Handling**: Taiwan-specific formats, enum conversions, null handling

## Module 1: Order Management (訂單管理)

### Legacy Table: `deliveries` → New Tables: `orders`, `order_items`

| Legacy Field | Legacy Type | New Field | New Type | Transformation | Notes |
|-------------|-------------|-----------|----------|----------------|-------|
| id | INTEGER | id | SERIAL | Direct map | Primary key |
| client_id | INTEGER | customer_id | INTEGER | Foreign key update | References customers.id |
| scheduled_date | DATE | scheduled_date | DATE | Direct map | |
| scheduled_time_start | VARCHAR(5) | delivery_time_start | TIME | Parse "HH:MM" to TIME | |
| scheduled_time_end | VARCHAR(5) | delivery_time_end | TIME | Parse "HH:MM" to TIME | |
| actual_delivery_time | DATETIME | delivered_at | TIMESTAMP | Timezone conversion | Convert to UTC |
| driver_id | INTEGER | driver_id | INTEGER | Direct map | |
| vehicle_id | INTEGER | route_id | INTEGER | Map through routes table | |
| status | VARCHAR(11) | status | ENUM | Map to OrderStatus enum | See status mapping below |
| delivered_50kg | INTEGER | → order_items | | Split to order_items | |
| delivered_20kg | INTEGER | → order_items | | Split to order_items | |
| delivered_16kg | INTEGER | → order_items | | Split to order_items | |
| delivered_10kg | INTEGER | → order_items | | Split to order_items | |
| delivered_4kg | INTEGER | → order_items | | Split to order_items | |
| returned_50kg | INTEGER | → order_items | | Track as negative qty | |
| returned_20kg | INTEGER | → order_items | | Track as negative qty | |
| returned_16kg | INTEGER | → order_items | | Track as negative qty | |
| returned_10kg | INTEGER | → order_items | | Track as negative qty | |
| returned_4kg | INTEGER | → order_items | | Track as negative qty | |
| notes | TEXT | delivery_notes | TEXT | Big5 → UTF-8 | |
| signature_url | VARCHAR(500) | signature_url | VARCHAR | Direct map | |
| photo_url | VARCHAR(500) | → delivery_photos | | New related table | |
| route_sequence | INTEGER | route_sequence | INTEGER | Direct map | |
| distance_km | FLOAT | estimated_distance | DECIMAL(10,2) | Direct map | |
| estimated_duration_minutes | INTEGER | estimated_duration | INTEGER | Direct map | |

#### Status Mapping
```
Legacy → New:
'pending' → OrderStatus.PENDING
'confirmed' → OrderStatus.CONFIRMED  
'in_delivery' → OrderStatus.IN_DELIVERY
'delivered' → OrderStatus.DELIVERED
'cancelled' → OrderStatus.CANCELLED
'failed' → OrderStatus.FAILED
```

#### Order Items Creation
For each cylinder type with quantity > 0, create an order_item:
```python
# Example transformation
if delivered_50kg > 0:
    create_order_item(
        order_id=new_order_id,
        gas_product_id=lookup_product('50kg'),
        quantity=delivered_50kg,
        is_exchange=returned_50kg > 0,
        empty_received=returned_50kg
    )
```

## Module 2: Route Planning (路線規劃)

### Legacy Table: `routes` → New Table: `routes`

| Legacy Field | Legacy Type | New Field | New Type | Transformation | Notes |
|-------------|-------------|-----------|----------|----------------|-------|
| id | INTEGER | id | SERIAL | Direct map | |
| route_date | DATE | route_date | DATE | Direct map | |
| route_name | VARCHAR(100) | route_name | VARCHAR(100) | Big5 → UTF-8 | |
| area | VARCHAR(50) | area | VARCHAR(50) | Big5 → UTF-8 | Map to districts |
| driver_id | INTEGER | driver_id | INTEGER | Direct map | |
| vehicle_id | INTEGER | vehicle_id | INTEGER | Direct map | |
| total_clients | INTEGER | total_stops | INTEGER | Direct map | |
| total_distance_km | FLOAT | total_distance | DECIMAL(10,2) | Direct map | |
| estimated_duration_minutes | INTEGER | estimated_duration | INTEGER | Direct map | |
| is_optimized | BOOLEAN | is_optimized | BOOLEAN | Direct map | |
| optimization_score | FLOAT | optimization_score | DECIMAL(5,2) | Direct map | |
| route_details | TEXT | route_polyline | TEXT | Parse JSON → polyline | |
| created_at | DATETIME | created_at | TIMESTAMP | Timezone conversion | |
| updated_at | DATETIME | updated_at | TIMESTAMP | Timezone conversion | |

### Legacy Table: `drivers` → New Table: `users` (with role='driver')

| Legacy Field | Legacy Type | New Field | New Type | Transformation | Notes |
|-------------|-------------|-----------|----------|----------------|-------|
| id | INTEGER | id | SERIAL | New ID mapping | Store mapping table |
| name | VARCHAR(100) | full_name | VARCHAR(100) | Big5 → UTF-8 | |
| phone | VARCHAR(20) | phone | VARCHAR(20) | Validate Taiwan format | |
| employee_id | VARCHAR(50) | employee_id | VARCHAR(50) | Direct map | |
| license_type | VARCHAR(50) | driver_license_type | VARCHAR(50) | Big5 → UTF-8 | |
| is_active | BOOLEAN | is_active | BOOLEAN | Direct map | |
| is_available | BOOLEAN | is_available | BOOLEAN | Direct map | |
| experience_years | INTEGER | driver_experience_years | INTEGER | Direct map | |
| familiar_areas | TEXT | driver_familiar_areas | TEXT[] | Parse to array | |
| created_at | DATETIME | created_at | TIMESTAMP | Timezone conversion | |
| updated_at | DATETIME | updated_at | TIMESTAMP | Timezone conversion | |
| - | - | email | VARCHAR(255) | Generate from employee_id | employee_id@luckygas.tw |
| - | - | role | ENUM | Set to 'driver' | |
| - | - | password | VARCHAR | Generate secure password | Must be reset on first login |

## Module 3: Inventory Management (庫存管理)

### New Table Structure: `inventory_transactions`, `warehouse_stock`, `cylinder_tracking`

Since legacy system tracks inventory inline with deliveries, we need to reconstruct:

| Source | Calculation | New Field | New Type | Notes |
|--------|-------------|-----------|----------|-------|
| deliveries.delivered_* | Sum by date | quantity_out | INTEGER | Outbound transactions |
| deliveries.returned_* | Sum by date | quantity_in | INTEGER | Inbound transactions |
| - | Generate | transaction_type | ENUM | 'delivery', 'return', 'adjustment' |
| - | Generate | warehouse_id | INTEGER | Default to main warehouse |
| - | Generate | gas_product_id | INTEGER | Map from cylinder size |
| deliveries.scheduled_date | Direct | transaction_date | DATE | |
| - | Calculate | running_balance | INTEGER | Calculate from transactions |

### Cylinder Serial Number Tracking
```sql
-- Extract from notes field if contains serial numbers
-- Pattern: "鋼瓶號碼: XXXX-XXXX-XXXX"
```

## Module 4: Billing/Invoicing (帳務/發票)

### New Table Structure: `invoices`, `invoice_items`, `payments`

Generate from delivery history:

| Source | Calculation | New Field | New Type | Notes |
|--------|-------------|-----------|----------|-------|
| deliveries.id | Map | order_id | INTEGER | Link to order |
| deliveries.client_id | Map | customer_id | INTEGER | |
| deliveries.scheduled_date | Direct | invoice_date | DATE | |
| - | Generate | invoice_number | VARCHAR(20) | Format: INV-YYYYMM-XXXXX |
| - | Calculate | subtotal | DECIMAL(10,2) | Sum of items |
| - | Calculate | tax_amount | DECIMAL(10,2) | subtotal * 0.05 |
| - | Calculate | total_amount | DECIMAL(10,2) | subtotal + tax |
| clients.payment_method | Map | payment_terms | ENUM | Map to payment terms |
| - | Set | status | ENUM | Default 'unpaid' |
| - | Generate | due_date | DATE | Based on payment terms |

### Taiwan E-Invoice Fields
| Field | Type | Notes |
|-------|------|-------|
| einvoice_number | VARCHAR(10) | Format: XX12345678 |
| einvoice_track | VARCHAR(2) | 2-letter track code |
| buyer_tax_id | VARCHAR(8) | From customer |
| carrier_type | VARCHAR(10) | 手機條碼, 自然人憑證 |
| carrier_id | VARCHAR(64) | Encrypted carrier |

## Module 5: Reporting/Analytics (報表/分析)

### Data Warehouse Tables: `fact_deliveries`, `dim_date`, `dim_customer`, `dim_product`

Transform transactional data to analytical format:

| Source | New Field | New Type | Aggregation | Notes |
|--------|-----------|----------|-------------|-------|
| deliveries.* | fact_delivery_id | SERIAL | - | Fact table primary key |
| deliveries.scheduled_date | date_key | INTEGER | Link to dim_date | YYYYMMDD format |
| deliveries.client_id | customer_key | INTEGER | Link to dim_customer | |
| delivered_* columns | product_key | INTEGER | Link to dim_product | One row per product |
| delivered_* columns | quantity | INTEGER | Direct | |
| - | revenue | DECIMAL(10,2) | Calculate from pricing | |
| deliveries.distance_km | delivery_distance | DECIMAL(10,2) | Direct | |
| deliveries.estimated_duration_minutes | delivery_duration | INTEGER | Direct | |
| deliveries.status | is_successful | BOOLEAN | status = 'delivered' | |

### Aggregated Metrics Table: `customer_metrics`
| Metric | Calculation | Update Frequency |
|--------|-------------|------------------|
| total_orders | COUNT(*) | Daily |
| total_revenue | SUM(revenue) | Daily |
| avg_order_value | AVG(revenue) | Daily |
| delivery_frequency | AVG days between orders | Weekly |
| churn_risk_score | ML model output | Weekly |

## Module 6: User Management (使用者管理)

### Legacy System Users → New Table: `users`

Map existing users and generate new ones:

| User Type | Legacy Source | New Role | Permissions | Notes |
|-----------|---------------|----------|-------------|-------|
| Drivers | drivers table | driver | view_routes, update_delivery | |
| Office Staff | Hardcoded | office_staff | manage_orders, manage_customers | Generate from employee list |
| Managers | Hardcoded | manager | all_except_system | Generate from employee list |
| Customers | clients table | customer | view_own_orders | Optional portal access |
| System Admin | - | super_admin | all_permissions | Create during migration |

### Permission Mapping
```python
ROLE_PERMISSIONS = {
    'super_admin': ['*'],
    'manager': [
        'view_all_orders', 'edit_orders', 'view_reports',
        'manage_routes', 'manage_drivers', 'view_analytics'
    ],
    'office_staff': [
        'view_orders', 'create_orders', 'edit_orders',
        'view_customers', 'edit_customers'
    ],
    'driver': [
        'view_assigned_routes', 'update_delivery_status',
        'upload_photos', 'view_customer_details'
    ],
    'customer': [
        'view_own_orders', 'track_delivery',
        'view_invoices', 'update_profile'
    ]
}
```

## Module 7: System Configuration (系統設定)

### Configuration Migration

Create new configuration tables:

| Category | Legacy Storage | New Table | New Fields | Notes |
|----------|---------------|-----------|------------|-------|
| Business Rules | Hardcoded | system_config | key, value, category | JSON values |
| Pricing | Hardcoded | pricing_rules | product_id, customer_type, price | Flexible pricing |
| Areas | Hardcoded | service_areas | area_code, area_name, is_active | Taiwan districts |
| Holidays | Manual | taiwan_holidays | date, name, is_working_day | Government holidays |
| Parameters | Various | system_parameters | Various typed fields | Strongly typed |

### Key Configuration Items
```yaml
business_hours:
  start: "08:00"
  end: "18:00"
  
delivery_windows:
  - { start: "08:00", end: "10:00", surcharge: 0 }
  - { start: "10:00", end: "12:00", surcharge: 0 }
  - { start: "13:00", end: "15:00", surcharge: 0 }
  - { start: "15:00", end: "17:00", surcharge: 0 }
  - { start: "17:00", end: "19:00", surcharge: 50 }
  
cylinder_sizes:
  - { size: 50, unit: "kg", deposit: 3000 }
  - { size: 20, unit: "kg", deposit: 2000 }
  - { size: 16, unit: "kg", deposit: 1800 }
  - { size: 10, unit: "kg", deposit: 1500 }
  - { size: 4, unit: "kg", deposit: 1000 }
  
payment_terms:
  - { code: "cash", name: "現金", days: 0 }
  - { code: "credit", name: "月結", days: 30 }
  - { code: "transfer", name: "轉帳", days: 7 }
```

## Data Validation Rules

### 1. Required Field Validation
- All primary keys must be non-null
- Customer references must exist
- Dates must be valid and within business range

### 2. Business Logic Validation
- Delivery quantities must be positive
- Return quantities cannot exceed delivered
- Scheduled dates cannot be in past (for new orders)
- Phone numbers must match Taiwan format

### 3. Encoding Validation
- All text fields must convert cleanly from Big5 to UTF-8
- Special characters (。,（）) must be preserved
- Address fields must contain valid Taiwan address components

### 4. Referential Integrity
- All foreign keys must have valid references
- Orphaned records must be logged and handled
- Circular references must be detected and resolved

## Migration Scripts Structure

```python
# migrations/migrate_orders.py
class OrderMigration:
    def __init__(self, source_db, target_db):
        self.source = source_db
        self.target = target_db
        self.encoding = 'big5'
        self.errors = []
        
    def migrate(self):
        # 1. Extract from legacy
        # 2. Transform data
        # 3. Validate
        # 4. Load to new system
        # 5. Verify migration
```

## Special Considerations

### 1. Taiwan-Specific Data
- Phone number formats: 09XX-XXX-XXX or 0X-XXXX-XXXX
- Address parsing: Extract district, road, number
- Tax ID validation: 8-digit with checksum
- E-invoice integration: Track and number fields

### 2. Performance Optimization
- Batch processing: 1000 records at a time
- Parallel processing: By date range or customer group
- Index creation: After bulk load
- Constraint validation: Deferred until end

### 3. Rollback Strategy
- Transaction boundaries per module
- Checkpoint after each major table
- Ability to resume from failure point
- Complete audit trail of migration

## Next Steps

1. Create Big5 to UTF-8 conversion utilities
2. Build validation framework
3. Implement incremental sync mechanism
4. Create migration scripts for each module
5. Set up migration monitoring dashboard