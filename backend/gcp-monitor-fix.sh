#!/bin/bash
# Date conversion function that works on both Linux and macOS
# This function replaces the GNU date -d syntax with portable alternatives

# Function to convert ISO date to epoch seconds (portable)
date_to_epoch() {
    local date_string="$1"
    
    # Check if we're on macOS or Linux
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS uses -j flag and different format
        # Convert ISO format to macOS format
        # Example: 2025-07-21T21:36:52Z -> 20250721213652
        local formatted_date=$(echo "$date_string" | sed -E 's/([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z?/\1\2\3\4\5\6/')
        date -j -f "%Y%m%d%H%M%S" "$formatted_date" "+%s" 2>/dev/null || echo "0"
    else
        # Linux/GNU date
        date -d "$date_string" +%s 2>/dev/null || echo "0"
    fi
}

# Test the function
echo "Testing date conversion function..."
test_date="2025-07-21T21:36:52Z"
echo "Input date: $test_date"
epoch=$(date_to_epoch "$test_date")
echo "Epoch seconds: $epoch"

# Calculate age in days
current_epoch=$(date +%s)
age_days=$(( (current_epoch - epoch) / 86400 ))
echo "Age in days: $age_days"

echo ""
echo "To fix gcp-monitor.sh, replace line 101 with:"
echo 'local key_epoch=$(date_to_epoch "$oldest_key")'
echo 'local key_age_days=$(( ($(date +%s) - key_epoch) / 86400 ))'