#!/bin/bash

# Lucky Gas E2E Test Runner
# This script runs the Playwright E2E tests and generates a report

echo "======================================"
echo "Lucky Gas E2E Test Suite"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if Playwright is installed
check_playwright() {
    if ! npx playwright --version > /dev/null 2>&1; then
        echo -e "${YELLOW}Playwright not installed. Installing...${NC}"
        npm run playwright:install
    else
        echo -e "${GREEN}✓ Playwright is installed${NC}"
    fi
}

# Function to run tests
run_tests() {
    local test_type=$1
    local test_name=$2
    
    echo ""
    echo -e "${YELLOW}Running $test_name...${NC}"
    
    if npm run test:e2e:$test_type; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        return 1
    fi
}

# Main execution
main() {
    # Check and install Playwright if needed
    check_playwright
    
    # Create test results directory
    mkdir -p test-results
    mkdir -p test-results/screenshots
    
    echo ""
    echo "======================================"
    echo "Starting E2E Tests"
    echo "======================================"
    
    # Track test results
    FAILED_TESTS=0
    
    # Run authentication tests
    if ! run_tests "auth" "Authentication Tests"; then
        ((FAILED_TESTS++))
    fi
    
    # Run Order Management tests
    if ! run_tests "orders" "Order Management Tests"; then
        ((FAILED_TESTS++))
    fi
    
    # Run API integration tests
    if ! run_tests "api" "API Integration Tests"; then
        ((FAILED_TESTS++))
    fi
    
    echo ""
    echo "======================================"
    echo "Test Summary"
    echo "======================================"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
    else
        echo -e "${RED}✗ $FAILED_TESTS test suite(s) failed${NC}"
    fi
    
    # Generate HTML report
    echo ""
    echo -e "${YELLOW}Generating HTML report...${NC}"
    npm run test:e2e:report
    
    echo ""
    echo "======================================"
    echo "Test execution complete!"
    echo "View the report: npm run test:e2e:report"
    echo "======================================"
    
    exit $FAILED_TESTS
}

# Parse command line arguments
case "$1" in
    --auth)
        check_playwright
        run_tests "auth" "Authentication Tests"
        ;;
    --orders)
        check_playwright
        run_tests "orders" "Order Management Tests"
        ;;
    --api)
        check_playwright
        run_tests "api" "API Integration Tests"
        ;;
    --ui)
        check_playwright
        echo "Opening Playwright UI mode..."
        npm run test:e2e:ui
        ;;
    --debug)
        check_playwright
        echo "Running tests in debug mode..."
        npm run test:e2e:debug
        ;;
    --help)
        echo "Usage: ./run-e2e-tests.sh [option]"
        echo ""
        echo "Options:"
        echo "  --auth    Run authentication tests only"
        echo "  --orders  Run Order Management tests only"
        echo "  --api     Run API integration tests only"
        echo "  --ui      Open Playwright UI mode"
        echo "  --debug   Run tests in debug mode"
        echo "  --help    Show this help message"
        echo ""
        echo "No options: Run all tests"
        ;;
    *)
        main
        ;;
esac