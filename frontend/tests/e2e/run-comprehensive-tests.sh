#!/bin/bash

# Comprehensive Test Runner for Lucky Gas Application
# This script runs the intelligent Playwright test suite with error monitoring and automatic fixes

set -e

echo "🚀 Lucky Gas Comprehensive Test Suite"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TEST_ENV=${TEST_ENV:-"production"}
MAX_ITERATIONS=${MAX_ITERATIONS:-5}
BROWSER=${BROWSER:-"all"} # all, chromium, firefox, webkit

# Set environment variables
export VITE_API_URL=${VITE_API_URL:-"https://vast-tributary-466619-m8.web.app"}
export VITE_WS_URL=${VITE_WS_URL:-"wss://luckygas-backend-production-154687573210.asia-east1.run.app"}

echo "Configuration:"
echo "  Environment: $TEST_ENV"
echo "  Max Iterations: $MAX_ITERATIONS"
echo "  Browser: $BROWSER"
echo "  API URL: $VITE_API_URL"
echo ""

# Create necessary directories
mkdir -p test-results
mkdir -p screenshots
mkdir -p playwright-report

# Function to run tests
run_tests() {
    local test_file=$1
    local browser=$2
    
    echo -e "${YELLOW}Running tests: $test_file (Browser: $browser)${NC}"
    
    if [ "$browser" == "all" ]; then
        npx playwright test "$test_file" --project=chromium --project=firefox --project=webkit
    else
        npx playwright test "$test_file" --project="$browser"
    fi
}

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Install Playwright browsers if needed
echo "Ensuring Playwright browsers are installed..."
npx playwright install

# Clean previous results
echo "Cleaning previous test results..."
rm -rf test-results/*
rm -rf screenshots/*

echo ""
echo "Starting comprehensive test suite..."
echo "===================================="

# Run the comprehensive system test
echo -e "\n${GREEN}1. Running Comprehensive System Test${NC}"
run_tests "comprehensive-system-test.spec.ts" "$BROWSER"

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Comprehensive tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed. Checking for auto-fixable errors...${NC}"
    
    # Run fix application
    echo -e "\n${YELLOW}Applying automatic fixes...${NC}"
    npx playwright test comprehensive-system-test.spec.ts --grep "Apply and verify automatic fixes"
    
    # Re-run tests after fixes
    echo -e "\n${YELLOW}Re-running tests after fixes...${NC}"
    run_tests "comprehensive-system-test.spec.ts" "$BROWSER"
fi

# Generate reports
echo -e "\n${GREEN}Generating reports...${NC}"

# Generate HTML report
npx playwright show-report

# Find and display the latest report
LATEST_REPORT=$(ls -t test-results/report_*.md 2>/dev/null | head -1)
if [ -f "$LATEST_REPORT" ]; then
    echo -e "\n${GREEN}Test Report Summary:${NC}"
    echo "===================="
    # Extract summary from markdown report
    grep -A 5 "## Summary" "$LATEST_REPORT" || true
    echo ""
    echo "Full report available at: $LATEST_REPORT"
fi

# Find and display error reports
ERROR_REPORTS=$(ls test-results/errors_*.md 2>/dev/null)
if [ -n "$ERROR_REPORTS" ]; then
    echo -e "\n${YELLOW}Error Reports Generated:${NC}"
    for report in $ERROR_REPORTS; do
        echo "  - $report"
    done
fi

# Display performance metrics
echo -e "\n${GREEN}Performance Metrics:${NC}"
echo "===================="
if [ -f "test-results/results.json" ]; then
    # Extract performance metrics from JSON (requires jq)
    if command -v jq &> /dev/null; then
        jq '.suites[0].specs[].tests[].results[].attachments[] | select(.name == "performance") | .body' test-results/results.json 2>/dev/null || echo "No performance data available"
    else
        echo "Install 'jq' for detailed performance metrics"
    fi
fi

# Check for critical errors
CRITICAL_ERRORS=$(grep -c "CRITICAL" test-results/errors_*.md 2>/dev/null || echo "0")
if [ "$CRITICAL_ERRORS" -gt "0" ]; then
    echo -e "\n${RED}⚠️  WARNING: $CRITICAL_ERRORS critical errors found!${NC}"
    echo "Please review the error reports for details."
    exit 1
else
    echo -e "\n${GREEN}✅ No critical errors found!${NC}"
fi

# Display recommendations
echo -e "\n${GREEN}Recommendations:${NC}"
echo "=================="
if [ -f "$LATEST_REPORT" ]; then
    grep -A 10 "## Recommendations" "$LATEST_REPORT" | tail -n +2 || echo "No recommendations available"
fi

echo ""
echo "===================================="
echo -e "${GREEN}Test suite completed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review the HTML report: npx playwright show-report"
echo "  2. Check error reports in: test-results/"
echo "  3. Review screenshots in: screenshots/"
echo "  4. Apply suggested fixes if any"
echo ""

# Return appropriate exit code
if [ "$CRITICAL_ERRORS" -gt "0" ]; then
    exit 1
else
    exit 0
fi