#!/bin/bash
# Test the date conversion fix

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

# Test with the same format from gcloud
test_date="2025-07-21T21:36:52Z"
echo "Testing with: $test_date"
key_epoch=$(date_to_epoch "$test_date")
echo "Epoch: $key_epoch"

if [ "$key_epoch" -ne 0 ]; then
    current_epoch=$(date +%s)
    key_age_days=$(( (current_epoch - key_epoch) / 86400 ))
    echo "Age in days: $key_age_days"
    echo "SUCCESS: Date conversion works!"
else
    echo "ERROR: Date conversion failed"
fi