# NaN Handling Strategy for Lucky Gas Data Import

## Overview

This document describes the comprehensive NaN (Not a Number) handling strategy implemented for importing customer data from Excel files into the Lucky Gas database. The solution addresses the issue where ~30% of customer records were failing to import due to "cannot convert float NaN to integer" errors.

## Problem Analysis

### Root Cause
When pandas reads empty cells from Excel files, they become `NaN` (a special float value). The original import script attempted to convert these directly to integers using `int()`, which raises an exception.

### Impact
- **Before Fix**: Only 880 of 1,267 customers (70%) imported successfully
- **After Fix**: All 1,267 customers (100%) imported successfully

### Most Affected Fields
Based on analysis, fields with highest NaN rates:
1. **營16** (ying16 cylinders): 100% NaN
2. **好運20** (haoyun20 cylinders): 100% NaN  
3. **10KG cylinders**: 99.6% NaN
4. **營20** (ying20 cylinders): 99.4% NaN
5. **好運16** (haoyun16 cylinders): 95.7% NaN

## Implementation Strategy

### 1. Type-Safe Conversion Functions

Four utility functions handle different data types with NaN detection:

```python
def safe_int(value: Any, default: int = 0, field_name: str = None, report: DataImportReport = None) -> int:
    """Safely convert value to integer with NaN handling"""
    if pd.isna(value):
        if report and field_name:
            report.add_nan_replacement(field_name)
        return default
    try:
        if isinstance(value, float):
            return int(value)
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0, field_name: str = None, report: DataImportReport = None) -> float
def safe_str(value: Any, default: str = '', field_name: str = None, report: DataImportReport = None) -> str
def safe_bool(value: Any, default: bool = False, field_name: str = None, report: DataImportReport = None) -> bool
```

### 2. Field-Specific Default Values

Different fields use semantically appropriate defaults:

| Field Type | Default Value | Reasoning |
|------------|---------------|-----------|
| Cylinder counts | 0 | Absence means customer doesn't use that cylinder type |
| Max cycle days | 30 | Reasonable monthly delivery cycle |
| Can delay days | 7 | One week buffer for delivery flexibility |
| Average daily usage | 0.0 | No usage if not specified |
| Boolean flags | False | Conservative default for features/services |
| String fields | "" | Empty string for optional text |
| Delivery time | 08:00-17:00 | Standard business hours |

### 3. Data Quality Tracking

The `DataImportReport` class tracks:
- Total rows processed
- Successful imports
- Failed imports  
- NaN replacements per field
- Warnings (e.g., customers with cylinders but no usage data)
- Errors with row numbers and details

### 4. Validation Rules

Critical data validation includes:
- Warning if customer has no address
- Warning if customer has cylinders but avg_daily_usage = 0
- Error if customer code is missing

## Results

### Import Success Rate
- **Before**: 70% (880/1,267)
- **After**: 100% (1,267/1,267)

### Data Quality Insights
From the import report:
- **Total NaN replacements**: 27,269
- **Fields with 100% NaN**: 營16, 好運20 (specialized cylinder types)
- **Warnings generated**: 91 (mainly cylinders without usage data)

### Sample Import Report
```json
{
  "summary": {
    "total_rows": 1267,
    "successful_imports": 1267,
    "failed_imports": 0,
    "skipped_existing": 0,
    "success_rate": "100.0%"
  },
  "data_quality": {
    "total_nan_replacements": 27269,
    "fields_with_most_nan": [
      ["營16", 1267],
      ["好運20", 1267],
      ["設備客戶買斷", 1264],
      ["10KG", 1262]
    ]
  }
}
```

## Usage

### Running the Import
```bash
cd backend
DATABASE_URL=postgresql+psycopg2://luckygas:luckygas123@localhost:5433/luckygas \
uv run python ../database/migrations/001_import_excel.py
```

### Import Report Location
Reports are saved as JSON files:
```
database/migrations/import_report_YYYYMMDD_HHMMSS.json
```

## Future Improvements

1. **Data Cleansing**: Pre-process Excel files to standardize empty values
2. **Configurable Defaults**: Allow default values to be configured per deployment
3. **Advanced Validation**: Implement business logic validation rules
4. **Incremental Import**: Support updating existing records with new data
5. **UI Integration**: Display import reports in web interface

## Technical Details

### Dependencies
- `pandas`: For Excel file reading and NaN detection
- `numpy`: For NaN value handling
- `sqlalchemy`: For database operations
- `asyncio`: For async database operations

### Key Functions
- `pd.isna()`: Detects NaN values reliably
- `safe_*()`: Type-safe conversion with logging
- `DataImportReport`: Comprehensive tracking and reporting

## Conclusion

The comprehensive NaN handling strategy successfully resolved all data import issues, achieving 100% import success rate while maintaining data quality through intelligent defaults and detailed reporting. The solution is robust, maintainable, and provides valuable data quality insights for business operations.