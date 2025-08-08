# Lucky Gas Data Migration - Edge Case Handling Guide

**Prepared by**: Mary (Business Analyst)  
**Date**: 2025-01-29  
**Purpose**: Comprehensive guide for handling edge cases during data migration

## 🎯 Overview

This guide provides detailed strategies for handling edge cases discovered in the Lucky Gas data. Each edge case includes detection methods, recommended handling approaches, and fallback options.

## 📊 Edge Case Categories

### 1. Data Quality Edge Cases

#### 1.1 Duplicate Customer Records
**Detection Method**:
```sql
-- Find exact duplicates (same tax ID)
SELECT tax_id, COUNT(*) as duplicate_count
FROM raw_customers
WHERE tax_id IS NOT NULL
GROUP BY tax_id
HAVING COUNT(*) > 1;

-- Find probable duplicates (name + phone)
SELECT customer_name, phone, COUNT(*) as duplicate_count
FROM raw_customers
GROUP BY customer_name, phone
HAVING COUNT(*) > 1;
```

**Handling Strategy**:
```python
def handle_duplicate_customers(duplicates):
    """
    Merge duplicate customer records intelligently
    """
    merge_strategy = {
        'selection_criteria': [
            'most_recent_activity',      # Primary
            'highest_transaction_volume', # Secondary
            'most_complete_data'         # Tertiary
        ],
        'field_merging': {
            'contact_info': 'keep_all_unique',
            'addresses': 'keep_all_as_delivery_points',
            'cylinders': 'sum_all_quantities',
            'credit_limit': 'use_highest',
            'payment_terms': 'use_most_favorable',
            'delivery_history': 'combine_all'
        }
    }
    
    for duplicate_set in duplicates:
        master_record = select_master_record(duplicate_set, merge_strategy)
        merged_data = merge_records(duplicate_set, master_record, merge_strategy)
        
        # Create audit trail
        audit_log.record({
            'action': 'customer_merge',
            'master_id': master_record.id,
            'merged_ids': [r.id for r in duplicate_set],
            'merge_rules': merge_strategy,
            'timestamp': datetime.now()
        })
        
    return merged_data
```

#### 1.2 Invalid/Missing Phone Numbers
**Detection Method**:
```python
def detect_phone_issues(customer_record):
    issues = []
    
    phone = customer_record.get('phone', '')
    
    # Check for missing
    if not phone or phone.strip() == '':
        issues.append('missing_phone')
    
    # Check for invalid format
    elif not re.match(r'^0[2-9]-?\d{4}-?\d{4}$|^09\d{2}-?\d{3}-?\d{3}$', phone):
        issues.append('invalid_format')
    
    # Check for obviously fake numbers
    elif phone in ['0000-000-000', '1234-567-890', '0900-000-000']:
        issues.append('fake_number')
    
    # Check for disconnected number patterns
    elif phone.startswith('09') and phone[2:4] in ['00', '11']:
        issues.append('possibly_disconnected')
    
    return issues
```

**Handling Strategy**:
```python
def handle_phone_issues(customer, issues):
    """
    Handle various phone number issues with business logic
    """
    if 'missing_phone' in issues:
        # Check alternate phone fields
        alternates = [
            customer.get('mobile'),
            customer.get('phone2'),
            customer.get('contact_phone'),
            customer.get('emergency_phone')
        ]
        
        valid_alternate = None
        for alt in alternates:
            if alt and validate_taiwan_phone(alt)[0]:
                valid_alternate = alt
                break
        
        if valid_alternate:
            customer['phone'] = valid_alternate
            customer['phone_source'] = 'alternate_field'
        else:
            customer['phone'] = 'NO-PHONE-RECORDED'
            customer['requires_update'] = True
            customer['update_priority'] = 'HIGH'
    
    elif 'invalid_format' in issues:
        # Attempt to fix common formatting issues
        fixed_phone = fix_phone_format(customer['phone'])
        if fixed_phone:
            customer['phone'] = fixed_phone
            customer['phone_fixed'] = True
        else:
            customer['phone_invalid'] = True
            customer['original_phone'] = customer['phone']
            customer['phone'] = 'INVALID-' + customer['phone'][:10]
    
    return customer
```

#### 1.3 Malformed Dates
**Detection Method**:
```python
def detect_date_issues(date_value):
    """
    Detect various date format issues in Taiwan calendar system
    """
    issues = []
    
    if not date_value:
        return ['missing_date']
    
    date_str = str(date_value)
    
    # Taiwan calendar year format (e.g., 1130125)
    if len(date_str) == 7:
        year = date_str[:3]
        month = date_str[3:5]
        day = date_str[5:7]
        
        if not year.isdigit() or int(year) < 100 or int(year) > 120:
            issues.append('invalid_year')
        
        if not month.isdigit() or int(month) < 1 or int(month) > 12:
            issues.append('invalid_month')
        
        if not day.isdigit() or int(day) < 1 or int(day) > 31:
            issues.append('invalid_day')
    
    else:
        issues.append('invalid_format')
    
    return issues
```

**Handling Strategy**:
```python
def handle_date_issues(date_value, context):
    """
    Fix date issues with context-aware logic
    """
    if not date_value:
        # Use context to determine appropriate default
        if context == 'delivery_date':
            return None  # Will be filtered out
        elif context == 'customer_since':
            return datetime.now() - timedelta(days=365)  # Assume 1 year
    
    date_str = str(date_value)
    
    # Fix common typos
    if len(date_str) == 7:
        year = int(date_str[:3])
        month = int(date_str[3:5])
        day = int(date_str[5:7])
        
        # Fix impossible dates
        if day > 31:
            # Possible day/month swap
            if day <= 12 and month <= 31:
                day, month = month, day
            else:
                # Use last day of month
                day = calendar.monthrange(year + 1911, month)[1]
        
        # Convert to Western calendar
        try:
            western_date = datetime(year + 1911, month, day)
            return western_date
        except ValueError:
            # Last resort - use first day of month
            return datetime(year + 1911, month, 1)
    
    # Cannot fix - log for manual review
    return None
```

### 2. Business Logic Edge Cases

#### 2.1 Conflicting Customer Categories
**Scenario**: Customer marked as both residential and commercial

**Handling Strategy**:
```python
def resolve_customer_type_conflict(customer):
    """
    Resolve customer type conflicts using business indicators
    """
    indicators = {
        'commercial': 0,
        'residential': 0
    }
    
    # Check tax ID
    if customer.get('tax_id') and len(customer['tax_id']) == 8:
        indicators['commercial'] += 3
    
    # Check cylinder quantities
    total_cylinders = sum([
        customer.get('50kg', 0),
        customer.get('20kg', 0),
        customer.get('16kg', 0)
    ])
    
    if total_cylinders > 5:
        indicators['commercial'] += 2
    else:
        indicators['residential'] += 2
    
    # Check invoice title
    if customer.get('invoice_title') and customer['invoice_title'] != customer.get('name'):
        indicators['commercial'] += 2
    
    # Check address
    if any(keyword in customer.get('address', '') for keyword in ['工業區', '工廠', '餐廳', '公司']):
        indicators['commercial'] += 1
    
    # Determine type
    if indicators['commercial'] > indicators['residential']:
        customer['type'] = 'commercial'
        customer['sub_type'] = determine_commercial_subtype(customer)
    else:
        customer['type'] = 'residential'
    
    customer['type_confidence'] = max(indicators.values()) / sum(indicators.values())
    
    return customer
```

#### 2.2 Pricing Anomalies
**Scenario**: Prices significantly below cost or above market

**Handling Strategy**:
```python
def handle_pricing_anomalies(order_item):
    """
    Detect and handle unusual pricing
    """
    # Define normal price ranges by product
    price_ranges = {
        '50kg': {'min': 1600, 'max': 2500, 'cost': 1500},
        '20kg': {'min': 700, 'max': 1200, 'cost': 650},
        '16kg': {'min': 600, 'max': 1000, 'cost': 550},
        '10kg': {'min': 400, 'max': 700, 'cost': 380},
        '4kg': {'min': 180, 'max': 350, 'cost': 170}
    }
    
    product_type = order_item['product_type']
    unit_price = order_item['unit_price']
    
    if product_type in price_ranges:
        range_info = price_ranges[product_type]
        
        if unit_price < range_info['cost']:
            order_item['price_flag'] = 'BELOW_COST'
            order_item['requires_approval'] = True
            order_item['approval_reason'] = f"Price {unit_price} below cost {range_info['cost']}"
        
        elif unit_price < range_info['min']:
            order_item['price_flag'] = 'UNUSUALLY_LOW'
            order_item['discount_percentage'] = (range_info['min'] - unit_price) / range_info['min'] * 100
        
        elif unit_price > range_info['max']:
            order_item['price_flag'] = 'UNUSUALLY_HIGH'
            order_item['markup_percentage'] = (unit_price - range_info['max']) / range_info['max'] * 100
        
        else:
            order_item['price_flag'] = 'NORMAL'
    
    return order_item
```

#### 2.3 Impossible Delivery Combinations
**Scenario**: Delivery address outside service area but marked as delivered

**Handling Strategy**:
```python
def validate_delivery_feasibility(delivery_record):
    """
    Check if delivery was actually feasible
    """
    service_areas = load_service_areas()  # Postal codes we serve
    
    # Extract postal code from address
    postal_code = extract_postal_code(delivery_record['address'])
    
    if postal_code not in service_areas:
        # Check if it's a known exception
        if delivery_record.get('special_delivery_flag'):
            delivery_record['delivery_type'] = 'SPECIAL_ARRANGEMENT'
            delivery_record['extra_charge_likely'] = True
        
        # Check if it's a partner delivery
        elif any(partner in delivery_record.get('notes', '') for partner in ['合作', '轉送', '代送']):
            delivery_record['delivery_type'] = 'PARTNER_DELIVERY'
        
        # Check distance from nearest service area
        else:
            nearest_distance = calculate_nearest_service_area(postal_code)
            if nearest_distance < 5:  # km
                delivery_record['delivery_type'] = 'EXTENDED_SERVICE'
                delivery_record['requires_verification'] = True
            else:
                delivery_record['delivery_type'] = 'DATA_ERROR'
                delivery_record['likely_incorrect_address'] = True
    
    return delivery_record
```

### 3. Data Integrity Edge Cases

#### 3.1 Orphaned Records
**Scenario**: Delivery records with no matching customer

**Handling Strategy**:
```python
def handle_orphaned_deliveries(orphaned_records):
    """
    Attempt to match orphaned deliveries to customers
    """
    unmatched = []
    
    for delivery in orphaned_records:
        # Try multiple matching strategies
        matches = []
        
        # 1. Try fuzzy matching on customer name
        if delivery.get('customer_name'):
            name_matches = fuzzy_match_customer_name(
                delivery['customer_name'],
                threshold=0.85
            )
            matches.extend(name_matches)
        
        # 2. Try phone number matching
        if delivery.get('phone'):
            phone_matches = find_customers_by_phone(delivery['phone'])
            matches.extend(phone_matches)
        
        # 3. Try address matching
        if delivery.get('address'):
            address_matches = find_customers_by_address(
                delivery['address'],
                fuzzy=True
            )
            matches.extend(address_matches)
        
        if matches:
            # Score matches and pick best
            best_match = score_and_select_match(matches, delivery)
            delivery['matched_customer_id'] = best_match['customer_id']
            delivery['match_confidence'] = best_match['confidence']
            delivery['match_method'] = best_match['method']
            
            if best_match['confidence'] < 0.9:
                delivery['requires_verification'] = True
        else:
            # Create placeholder customer
            placeholder = create_placeholder_customer(delivery)
            delivery['matched_customer_id'] = placeholder['id']
            delivery['is_placeholder'] = True
            unmatched.append(delivery)
    
    return unmatched
```

#### 3.2 Circular References
**Scenario**: Customer A's alternate contact is Customer B, whose alternate is Customer A

**Handling Strategy**:
```python
def detect_and_break_circular_references(customers):
    """
    Detect and resolve circular reference chains
    """
    reference_graph = build_reference_graph(customers)
    
    # Find cycles using DFS
    cycles = find_cycles_in_graph(reference_graph)
    
    for cycle in cycles:
        # Determine which link to break
        # Prefer keeping references for active customers
        weakest_link = None
        min_score = float('inf')
        
        for i, customer_id in enumerate(cycle):
            next_id = cycle[(i + 1) % len(cycle)]
            
            # Score based on relationship strength
            score = calculate_reference_strength(customer_id, next_id)
            
            if score < min_score:
                min_score = score
                weakest_link = (customer_id, next_id)
        
        # Break the weakest link
        if weakest_link:
            remove_reference(weakest_link[0], weakest_link[1])
            log_circular_reference_resolution(cycle, weakest_link)
```

### 4. Performance Edge Cases

#### 4.1 Extremely Large Customer Orders
**Scenario**: Single customer with thousands of historical orders

**Handling Strategy**:
```python
def handle_high_volume_customer_migration(customer_id, order_count):
    """
    Special handling for customers with massive order history
    """
    if order_count > 10000:
        # Use batch processing
        batch_size = 1000
        
        migration_plan = {
            'strategy': 'BATCHED_MIGRATION',
            'batch_size': batch_size,
            'parallel_workers': 4,
            'priority_rules': [
                'Recent orders first (last 12 months)',
                'Then by year descending',
                'Archive orders > 5 years to cold storage'
            ]
        }
        
        # Create summary records for old data
        create_historical_summary(customer_id, older_than_years=5)
        
        # Migrate recent data in detail
        migrate_recent_orders_batched(customer_id, batch_size)
        
        return migration_plan
```

#### 4.2 Memory Constraints During Migration
**Scenario**: Running out of memory when processing large datasets

**Handling Strategy**:
```python
def memory_efficient_migration():
    """
    Use streaming and chunking for memory efficiency
    """
    # Use generators instead of loading all data
    def stream_customers():
        chunk_size = 1000
        offset = 0
        
        while True:
            chunk = read_customer_chunk(offset, chunk_size)
            if not chunk:
                break
            
            for customer in chunk:
                yield customer
            
            offset += chunk_size
            
            # Periodic garbage collection
            if offset % 10000 == 0:
                gc.collect()
    
    # Process in streaming fashion
    for customer in stream_customers():
        migrated_customer = process_customer(customer)
        save_customer_immediate(migrated_customer)
        
        # Don't keep in memory
        del customer
        del migrated_customer
```

## 🛡️ Safety Mechanisms

### 1. Validation Checkpoints
```python
class MigrationValidator:
    def __init__(self):
        self.checkpoints = []
        self.thresholds = {
            'record_count_variance': 0.01,  # 1%
            'financial_variance': 0.001,     # 0.1%
            'critical_field_null_rate': 0.001  # 0.1%
        }
    
    def add_checkpoint(self, name, validation_func):
        self.checkpoints.append({
            'name': name,
            'function': validation_func,
            'status': 'PENDING'
        })
    
    def validate_all(self):
        all_passed = True
        
        for checkpoint in self.checkpoints:
            try:
                result = checkpoint['function']()
                checkpoint['status'] = 'PASSED' if result['passed'] else 'FAILED'
                checkpoint['details'] = result.get('details', '')
                
                if not result['passed']:
                    all_passed = False
                    
            except Exception as e:
                checkpoint['status'] = 'ERROR'
                checkpoint['error'] = str(e)
                all_passed = False
        
        return all_passed, self.checkpoints
```

### 2. Rollback Triggers
```python
def should_rollback(validation_results):
    """
    Determine if migration should be rolled back
    """
    critical_failures = [
        'customer_count_mismatch',
        'financial_reconciliation_failed',
        'duplicate_key_violations',
        'referential_integrity_broken'
    ]
    
    for result in validation_results:
        if result['name'] in critical_failures and result['status'] == 'FAILED':
            return True, f"Critical failure: {result['name']}"
    
    # Check overall failure rate
    failure_count = sum(1 for r in validation_results if r['status'] == 'FAILED')
    failure_rate = failure_count / len(validation_results)
    
    if failure_rate > 0.1:  # 10% failure rate
        return True, f"High failure rate: {failure_rate:.1%}"
    
    return False, "No rollback needed"
```

### 3. Data Recovery Procedures
```python
def create_recovery_snapshot(stage_name):
    """
    Create a point-in-time snapshot for recovery
    """
    snapshot = {
        'stage': stage_name,
        'timestamp': datetime.now(),
        'record_counts': get_all_table_counts(),
        'checksums': calculate_table_checksums(),
        'sample_data': extract_sample_records()
    }
    
    # Save snapshot
    save_snapshot(snapshot)
    
    # Also create database backup
    create_database_backup(f"migration_{stage_name}_{snapshot['timestamp']}")
    
    return snapshot['id']
```

## 📊 Edge Case Metrics

### Key Metrics to Track
1. **Detection Rate**: % of edge cases successfully identified
2. **Resolution Rate**: % of edge cases successfully handled
3. **Manual Intervention Rate**: % requiring human review
4. **Performance Impact**: Processing time increase due to edge cases
5. **Data Quality Score**: Post-migration data quality metrics

### Reporting Template
```python
def generate_edge_case_report():
    report = {
        'summary': {
            'total_records_processed': 0,
            'edge_cases_detected': 0,
            'edge_cases_resolved': 0,
            'manual_review_required': 0
        },
        'by_category': {},
        'top_issues': [],
        'resolution_success_rate': 0,
        'recommendations': []
    }
    
    return report
```

---

**Important Notes**:
1. Always maintain an audit trail for edge case handling
2. Never silently discard data - always log or flag
3. When in doubt, flag for manual review
4. Test edge case handlers with real data samples
5. Monitor edge case patterns for system improvements