# Customer Edit Issue Analysis

## Summary

The customer edit functionality is failing with a 500 Internal Server Error, NOT a 403 permission error as originally thought.

## Root Cause

The frontend is sending fields that don't exist in the `CustomerUpdate` schema:

### Frontend sends (from transformToBackendSchema):
```javascript
{
  short_name: values.name,
  invoice_title: values.name,
  address: values.address,
  phone: values.phone,
  area: values.district,
  customer_type: values.customerType,  // ❌ NOT in CustomerUpdate
  cylinders_50kg: 0,
  cylinders_20kg: 0,
  cylinders_16kg: 0,
  cylinders_10kg: 0,
  cylinders_4kg: 0,
  is_terminated: values.status !== 'active',  // ❌ NOT in CustomerUpdate
  is_subscription: false,  // ❌ NOT in CustomerUpdate
  needs_same_day_delivery: false,  // ❌ NOT in CustomerUpdate
  delivery_time_start: values.deliveryTimeStart || '09:00',
  delivery_time_end: values.deliveryTimeEnd || '17:00'
}
```

### Backend CustomerUpdate schema expects:
- invoice_title ✅
- short_name ✅
- address ✅
- phone ✅
- tax_id
- cylinders_* ✅
- delivery_time_* ✅
- area ✅
- avg_daily_usage
- max_cycle_days

### Fields causing 500 error:
1. `customer_type` - Not in CustomerUpdate schema
2. `is_terminated` - Not in CustomerUpdate schema
3. `is_subscription` - Not in CustomerUpdate schema
4. `needs_same_day_delivery` - Not in CustomerUpdate schema

## Solution

The frontend needs to filter out fields that are not allowed in updates when sending PUT requests.

## Fixed Issues Along the Way

1. ✅ Phone validation - Removed dashes from phone numbers before form validation
2. ✅ Port configuration - Tests were using wrong port (5174 vs 5173)
3. ✅ Schema mismatch for customer creation (already fixed in previous iteration)

## Next Steps

1. Update the frontend `transformToBackendSchema` to check if it's an update operation
2. Filter out fields not allowed in CustomerUpdate schema for PUT requests
3. Test the fix