#!/bin/bash

# LuckyGas E2E Test Runner
# This script helps run the comprehensive E2E test suite

set -e

echo "🚀 LuckyGas E2E Test Suite Runner"
echo "================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed. Please install Node.js first.${NC}"
    exit 1
fi

# Navigate to test directory
cd "$(dirname "$0")"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    npm install
    npx playwright install --with-deps
fi

# Function to run tests
run_tests() {
    local test_type=$1
    local description=$2
    
    echo -e "\n${YELLOW}🧪 Running ${description}...${NC}"
    
    if npm run ${test_type}; then
        echo -e "${GREEN}✅ ${description} passed!${NC}"
    else
        echo -e "${RED}❌ ${description} failed!${NC}"
        exit 1
    fi
}

# Parse command line arguments
case "$1" in
    "all")
        echo "Running all tests..."
        run_tests "test" "All E2E Tests"
        ;;
    "auth")
        run_tests "test:auth" "Authentication Tests"
        ;;
    "customer")
        run_tests "test:customer" "Customer Journey Tests"
        ;;
    "driver")
        run_tests "test:driver" "Driver Workflow Tests"
        ;;
    "websocket")
        run_tests "test:websocket" "WebSocket Real-time Tests"
        ;;
    "mobile")
        run_tests "test:mobile" "Mobile Interface Tests"
        ;;
    "performance")
        run_tests "test:performance" "Performance Tests"
        ;;
    "visual")
        run_tests "test:visual" "Visual Regression Tests"
        ;;
    "debug")
        echo "Running tests in debug mode..."
        npm run test:debug
        ;;
    "ui")
        echo "Opening Playwright UI mode..."
        npm run test:ui
        ;;
    "report")
        echo "Opening test report..."
        npm run report
        ;;
    "help"|"")
        echo "Usage: ./run-tests.sh [command]"
        echo ""
        echo "Commands:"
        echo "  all         - Run all E2E tests"
        echo "  auth        - Run authentication tests only"
        echo "  customer    - Run customer journey tests only"
        echo "  driver      - Run driver workflow tests only"
        echo "  websocket   - Run WebSocket real-time tests only"
        echo "  mobile      - Run mobile interface tests"
        echo "  performance - Run performance tests"
        echo "  visual      - Run visual regression tests"
        echo "  debug       - Run tests in debug mode"
        echo "  ui          - Open Playwright UI mode"
        echo "  report      - Open HTML test report"
        echo "  help        - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run-tests.sh all        # Run complete test suite"
        echo "  ./run-tests.sh auth       # Run only auth tests"
        echo "  ./run-tests.sh debug      # Debug test execution"
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run './run-tests.sh help' for usage information"
        exit 1
        ;;
esac

# Show test report location if tests were run
if [ "$1" != "help" ] && [ "$1" != "ui" ] && [ "$1" != "debug" ]; then
    echo -e "\n${GREEN}📊 Test report available at: $(pwd)/playwright-report/index.html${NC}"
    echo -e "${GREEN}Run './run-tests.sh report' to open the report${NC}"
fi