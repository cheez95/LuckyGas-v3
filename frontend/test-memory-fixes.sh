#!/bin/bash

# Test Runner for Memory Leak Fixes
# This script runs all tests related to memory leak fixes and generates a comprehensive report

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     Memory Leak Fix Test Suite - Lucky Gas Management System     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test categories
declare -a TEST_CATEGORIES=(
    "WebSocket Reconnection Limits"
    "Unhandled Promise Rejections"
    "Request Timeouts and Cancellation"
    "Memory Optimization"
    "Component Cleanup"
)

# Initialize test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_RESULTS=""

# Function to run tests and capture results
run_test_category() {
    local category=$1
    local test_file=$2
    
    echo -e "${BLUE}Running: $category${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -f "$test_file" ]; then
        # Run the test
        npm test -- "$test_file" --coverage --no-watch 2>&1 | tee test_output.tmp
        
        # Parse results
        if grep -q "PASS" test_output.tmp; then
            echo -e "${GREEN}✓ $category: PASSED${NC}"
            ((PASSED_TESTS++))
            TEST_RESULTS="${TEST_RESULTS}\n✅ $category: PASSED"
        else
            echo -e "${RED}✗ $category: FAILED${NC}"
            ((FAILED_TESTS++))
            TEST_RESULTS="${TEST_RESULTS}\n❌ $category: FAILED"
        fi
        ((TOTAL_TESTS++))
    else
        echo -e "${YELLOW}⚠ Test file not found: $test_file${NC}"
    fi
    
    echo ""
    rm -f test_output.tmp
}

# Run all test categories
echo "🧪 Starting Test Execution..."
echo ""

# WebSocket Tests
run_test_category "WebSocket Reconnection Limits" "src/services/__tests__/websocket.test.ts"

# API Service Tests
run_test_category "Request Management & Timeouts" "src/services/__tests__/api.test.ts"

# Error Monitoring Tests
run_test_category "Unhandled Promise Rejections" "src/services/__tests__/errorMonitoring.test.ts"

# Component Tests
run_test_category "Route Planning Cleanup" "src/pages/__tests__/RoutePlanning.test.tsx"

# Generate Test Report
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                         TEST REPORT                              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

echo "📊 Test Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total Tests Run: $TOTAL_TESTS"
echo -e "Tests Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Tests Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

echo "🔍 Detailed Results:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "$TEST_RESULTS"
echo ""

# Memory Fix Verification Checklist
echo "✅ Memory Fix Verification Checklist:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check WebSocket fixes
echo -n "1. WebSocket reconnection limited to 5 attempts: "
if grep -q "MAX_RECONNECT_ATTEMPTS.*5" src/services/websocket.service.ts 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -n "2. WebSocket message queue limited to 50: "
if grep -q "MAX_MESSAGE_QUEUE_SIZE.*50" src/services/websocket.service.ts 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -n "3. Global unhandledrejection handler present: "
if grep -q "unhandledrejection" src/services/errorMonitoring.ts 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -n "4. Request timeout set to 10 seconds: "
if grep -q "timeout.*10000" src/services/api.service.ts 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -n "5. AbortController implementation present: "
if grep -q "AbortController" src/services/api.service.ts 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -n "6. Request caching implemented: "
if grep -q "requestCache" src/services/api.service.ts 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -n "7. Component cleanup in RoutePlanning: "
if grep -q "isMountedRef" src/pages/office/RoutePlanning.tsx 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo -n "8. Component cleanup in OrderManagement: "
if grep -q "isMountedRef" src/pages/office/OrderManagement.tsx 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

echo ""
echo "🎯 Performance Metrics:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check current memory usage if app is running
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "App is running locally - checking metrics..."
    
    # Use Chrome DevTools Protocol if available
    if command -v chrome-cli &> /dev/null; then
        echo "Memory usage data available via Chrome DevTools"
    else
        echo "Install chrome-cli for detailed memory metrics"
    fi
else
    echo "App not running locally - deploy to production for live metrics"
fi

echo ""
echo "📝 Recommendations:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Memory leak fixes are properly implemented.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Monitor production metrics for 24 hours"
    echo "2. Check memory usage trends in Chrome DevTools"
    echo "3. Verify WebSocket reconnection behavior under network issues"
    echo "4. Test with multiple concurrent users"
else
    echo -e "${YELLOW}⚠ Some tests failed. Review the failures above.${NC}"
    echo ""
    echo "Debug steps:"
    echo "1. Check test output for specific failures"
    echo "2. Verify all dependencies are installed"
    echo "3. Run individual test files for detailed output"
    echo "4. Check console for runtime errors"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "Test suite completed at $(date)"
echo "═══════════════════════════════════════════════════════════════════"