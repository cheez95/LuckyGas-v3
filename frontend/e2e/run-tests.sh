#!/bin/bash

# E2E Test Runner Script
# This script sets up and runs the E2E tests with proper environment configuration

set -e

echo "🧪 Lucky Gas E2E Test Runner"
echo "==========================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the e2e directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: Must run from the e2e directory${NC}"
    exit 1
fi

# Function to cleanup processes
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    
    # Kill test server if running
    if [ -f ".test-server.pid" ]; then
        PID=$(cat .test-server.pid)
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            echo "Stopped test server (PID: $PID)"
        fi
        rm .test-server.pid
    fi
    
    # Kill frontend dev server if running
    if [ -f ".frontend.pid" ]; then
        PID=$(cat .frontend.pid)
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            echo "Stopped frontend server (PID: $PID)"
        fi
        rm .frontend.pid
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing E2E test dependencies...${NC}"
    npm install
fi

# Check if TypeScript needs compilation
if [ ! -d "dist" ] || [ "setup/test-server.ts" -nt "dist/setup/test-server.js" ]; then
    echo -e "${YELLOW}Compiling TypeScript test server...${NC}"
    npm run build:server
fi

# Start the test server
echo -e "${GREEN}Starting test server...${NC}"
node dist/setup/test-server.js &
TEST_SERVER_PID=$!
echo $TEST_SERVER_PID > .test-server.pid

# Wait for test server to be ready
echo "Waiting for test server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:3001/health > /dev/null; then
        echo -e "${GREEN}Test server is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Test server failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Start frontend dev server if not already running
if ! curl -s http://localhost:5173 > /dev/null; then
    echo -e "${GREEN}Starting frontend dev server...${NC}"
    cd ..
    npm run dev > /dev/null 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > e2e/.frontend.pid
    cd e2e
    
    # Wait for frontend to be ready
    echo "Waiting for frontend to be ready..."
    for i in {1..60}; do
        if curl -s http://localhost:5173 > /dev/null; then
            echo -e "${GREEN}Frontend is ready!${NC}"
            break
        fi
        if [ $i -eq 60 ]; then
            echo -e "${RED}Frontend failed to start${NC}"
            exit 1
        fi
        sleep 1
    done
else
    echo -e "${GREEN}Frontend already running${NC}"
fi

# Run the tests
echo -e "\n${GREEN}Running E2E tests...${NC}"
echo "========================"

# Set environment variables
export VITE_API_URL=http://localhost:3001
export NODE_ENV=test

# Run playwright tests with options
if [ "$1" = "--ui" ]; then
    npx playwright test --ui
elif [ "$1" = "--debug" ]; then
    npx playwright test --debug
elif [ "$1" = "--headed" ]; then
    npx playwright test --headed
else
    npx playwright test
fi

TEST_EXIT_CODE=$?

# Show test report if tests completed
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
else
    echo -e "\n${RED}❌ Some tests failed${NC}"
    echo -e "${YELLOW}Run 'npm run test:report' to see detailed results${NC}"
fi

exit $TEST_EXIT_CODE