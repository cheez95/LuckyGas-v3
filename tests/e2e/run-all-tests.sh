#!/bin/bash

# Test Recovery Script for LuckyGas v3 E2E Tests
# This script runs all E2E tests with the mock backend

echo "🧪 LuckyGas v3 E2E Test Suite"
echo "============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if mock backend is running
check_mock_backend() {
    echo "🔍 Checking mock backend..."
    if curl -s http://localhost:3001/health > /dev/null; then
        echo -e "${GREEN}✓ Mock backend is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Mock backend not running${NC}"
        return 1
    fi
}

# Check if frontend is running
check_frontend() {
    echo "🔍 Checking frontend..."
    if curl -s http://localhost:5173 > /dev/null; then
        echo -e "${GREEN}✓ Frontend is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Frontend not running${NC}"
        return 1
    fi
}

# Start mock backend
start_mock_backend() {
    echo "🚀 Starting mock backend..."
    cd frontend/e2e
    node mock-backend.js &
    MOCK_PID=$!
    echo $MOCK_PID > .mock.pid
    sleep 3
    cd ../..
}

# Start frontend
start_frontend() {
    echo "🚀 Starting frontend..."
    cd frontend
    VITE_API_URL=http://localhost:3001 npm run dev &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../.frontend.pid
    sleep 5
    cd ..
}

# Stop services
stop_services() {
    echo ""
    echo "🛑 Stopping services..."
    
    # Stop mock backend
    if [ -f frontend/e2e/.mock.pid ]; then
        kill $(cat frontend/e2e/.mock.pid) 2>/dev/null
        rm frontend/e2e/.mock.pid
    fi
    
    # Stop frontend
    if [ -f .frontend.pid ]; then
        kill $(cat .frontend.pid) 2>/dev/null
        rm .frontend.pid
    fi
    
    # Also try to kill by port
    lsof -ti:3001 | xargs kill -9 2>/dev/null
    lsof -ti:5173 | xargs kill -9 2>/dev/null
}

# Run tests
run_tests() {
    echo ""
    echo "🧪 Running E2E tests..."
    echo ""
    
    cd tests/e2e
    
    # Run tests with simplified config
    npx playwright test \
        --config=playwright.config.simplified.ts \
        --project=chromium \
        --reporter=list \
        --reporter=html \
        auth.spec.ts customer.spec.ts orders.spec.ts
    
    TEST_RESULT=$?
    cd ../..
    
    return $TEST_RESULT
}

# Main execution
main() {
    echo "📋 Test Environment Setup"
    echo "========================"
    echo ""
    
    # Check services
    NEED_MOCK=false
    NEED_FRONTEND=false
    
    if ! check_mock_backend; then
        NEED_MOCK=true
    fi
    
    if ! check_frontend; then
        NEED_FRONTEND=true
    fi
    
    # Start services if needed
    if [ "$NEED_MOCK" = true ]; then
        start_mock_backend
    fi
    
    if [ "$NEED_FRONTEND" = true ]; then
        start_frontend
    fi
    
    # Give services time to stabilize
    sleep 2
    
    # Verify services are ready
    echo ""
    echo "📋 Service Status"
    echo "================"
    check_mock_backend
    check_frontend
    
    # Run tests
    run_tests
    TEST_RESULT=$?
    
    # Stop services if we started them
    if [ "$NEED_MOCK" = true ] || [ "$NEED_FRONTEND" = true ]; then
        read -p "Press Enter to stop services..."
        stop_services
    fi
    
    # Report results
    echo ""
    echo "📊 Test Results"
    echo "==============="
    if [ $TEST_RESULT -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
    else
        echo -e "${RED}❌ Some tests failed${NC}"
        echo ""
        echo "View detailed report: tests/e2e/playwright-report/index.html"
    fi
    
    exit $TEST_RESULT
}

# Handle Ctrl+C
trap stop_services INT

# Run main
main