# GCP Integration Test & Shell Script Errors - Resolution Report

## Issue Summary
The `gcp-test-integration.py` script references `gcp-monitor.sh` which contains GNU-specific date commands that fail on macOS, causing script execution errors.

## Root Cause Analysis

### 1. **Primary Issue: Date Command Incompatibility**
- **Location**: `gcp-monitor.sh` line 101
- **Problem**: Uses GNU date syntax `date -d` which is not supported on macOS
- **Error**: 
  ```
  date: illegal option -- d
  syntax error: operand expected (error token is ") / 86400 ")
  ```
- **Impact**: Script fails when calculating service account key age

### 2. **Secondary Issue: Missing Python Packages**
- **Problem**: GCP Python SDK packages not installed
- **Missing Packages**:
  - google-cloud-storage
  - google-cloud-aiplatform
  - google-cloud-secret-manager
  - google-auth

### 3. **Integration Issues**
- Python script doesn't check if monitoring script exists or is executable
- No error handling for shell script execution failures
- Verbose gcloud logging clutters output

## Solutions Implemented

### 1. **Fixed Date Command Compatibility**

Created a portable `date_to_epoch` function that works on both macOS and Linux:

```bash
# Function to convert ISO date to epoch seconds (portable for macOS and Linux)
date_to_epoch() {
    local date_string="$1"
    
    # Check if we're on macOS or Linux
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS uses -j flag and different format
        # Convert ISO format to macOS format
        local formatted_date=$(echo "$date_string" | sed -E 's/([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z?/\1\2\3\4\5\6/')
        date -j -f "%Y%m%d%H%M%S" "$formatted_date" "+%s" 2>/dev/null || echo "0"
    else
        # Linux/GNU date
        date -d "$date_string" +%s 2>/dev/null || echo "0"
    fi
}
```

### 2. **Updated Key Age Calculation**

Replaced the problematic line with:
```bash
if [ -n "$oldest_key" ]; then
    # Use portable date conversion
    local key_epoch=$(date_to_epoch "$oldest_key")
    if [ "$key_epoch" -ne 0 ]; then
        local key_age_days=$(( ($(date +%s) - key_epoch) / 86400 ))
        if [ "$key_age_days" -gt 90 ]; then
            print_status "warning" "Service account key older than 90 days ($key_age_days days)"
        fi
    else
        print_status "warning" "Could not parse key date: $oldest_key"
    fi
fi
```

### 3. **Enhanced Python Script Error Handling**

Added checks for shell script existence and permissions:
```python
# Check if monitoring script exists and is executable
monitor_script = Path(__file__).parent / "gcp-monitor.sh"
if monitor_script.exists():
    if os.access(monitor_script, os.X_OK):
        print("  - Monitor infrastructure: ./gcp-monitor.sh")
    else:
        print("  - Monitor infrastructure: bash gcp-monitor.sh")
        print_status("warning", f"Note: {monitor_script.name} is not executable. Run: chmod +x {monitor_script.name}")
else:
    print_status("warning", "Monitoring script not found: gcp-monitor.sh")
```

## Files Modified

1. **gcp-monitor.sh**:
   - Added `date_to_epoch` function (lines 66-80)
   - Updated key age calculation (lines 116-125)

2. **Created Support Files**:
   - `gcp-monitor-fix.sh` - Demonstrates the date conversion fix
   - `gcp-monitor.patch` - Patch file for the monitoring script
   - `gcp-test-integration-fix.patch` - Patch for Python script improvements
   - `test-date-fix.sh` - Test script to verify date conversion

## Testing Results

- ✅ Date conversion function works correctly on macOS
- ✅ Converts ISO 8601 timestamps to epoch seconds
- ✅ Calculates age in days properly
- ✅ Handles invalid dates gracefully (returns 0)

## Next Steps

### 1. **Install Missing Python Packages**
```bash
cd backend
uv pip install google-cloud-storage google-cloud-aiplatform google-cloud-secret-manager google-auth
```

### 2. **Apply Python Script Patch** (Optional)
```bash
patch gcp-test-integration.py < gcp-test-integration-fix.patch
```

### 3. **Set Environment Variables**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/lucky-gas/lucky-gas-prod-key.json
```

### 4. **Run Integration Tests**
```bash
python3 gcp-test-integration.py
```

## Best Practices

1. **Cross-Platform Compatibility**: Always test shell scripts on both Linux and macOS
2. **Use Portable Commands**: Avoid GNU-specific utilities when possible
3. **Error Handling**: Add proper error handling for external script execution
4. **Dependency Checks**: Verify required tools/packages before execution
5. **Verbose Logging**: Control verbosity with environment variables or flags

## Alternative Solutions

If issues persist:
1. Use Python's `datetime` module instead of shell date commands
2. Create separate scripts for Linux and macOS
3. Use Docker containers for consistent environment
4. Implement all monitoring logic in Python to avoid shell compatibility issues

---
**Generated**: 2025-07-22  
**Status**: RESOLVED  
**Platform**: macOS (Darwin)