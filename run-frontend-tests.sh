#!/bin/bash

# Lucky Gas Frontend E2E Test Runner (No Docker Required)
# This script runs E2E tests using a mock backend

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Lucky Gas Frontend E2E Tests - No Docker Required"
echo "===================================================="

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    if [ -n "$MOCK_BACKEND_PID" ]; then
        kill $MOCK_BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is not installed${NC}"
    exit 1
fi

# Install mock backend dependencies
echo -e "${YELLOW}Setting up mock backend...${NC}"
cd frontend/e2e
if [ ! -d "node_modules" ]; then
    npm init -y > /dev/null 2>&1
    npm install express cors jsonwebtoken --save > /dev/null 2>&1
fi

# Start mock backend
echo -e "${YELLOW}Starting mock backend server...${NC}"
node mock-backend.js &
MOCK_BACKEND_PID=$!
sleep 3

# Check if mock backend is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}Mock backend failed to start${NC}"
    exit 1
fi
echo -e "${GREEN}Mock backend is running!${NC}"

# Go back to frontend directory
cd ..

# Install frontend dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

# Install Playwright browsers if needed
if [ ! -d "node_modules/@playwright/test/.local-browsers" ]; then
    echo -e "${YELLOW}Installing Playwright browsers...${NC}"
    npx playwright install chromium
fi

# Start frontend dev server
echo -e "${YELLOW}Starting frontend dev server...${NC}"
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "Waiting for frontend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null; then
        echo -e "${GREEN}Frontend is ready!${NC}"
        break
    fi
    sleep 1
done

# Run E2E tests
echo -e "\n${YELLOW}Running E2E tests...${NC}"
echo "================================"

# Run specific test suites
test_failed=false

# Authentication tests
echo -e "\n${YELLOW}Running Authentication tests...${NC}"
if npm run test:e2e -- auth.spec.ts --project=chromium; then
    echo -e "${GREEN}✅ Authentication tests passed${NC}"
else
    echo -e "${RED}❌ Authentication tests failed${NC}"
    test_failed=true
fi

# Driver mobile tests
echo -e "\n${YELLOW}Running Driver Mobile tests...${NC}"
if npm run test:e2e -- driver-mobile.spec.ts --project="Mobile Chrome"; then
    echo -e "${GREEN}✅ Driver Mobile tests passed${NC}"
else
    echo -e "${RED}❌ Driver Mobile tests failed${NC}"
    test_failed=true
fi

# Predictions and routes tests
echo -e "\n${YELLOW}Running Predictions & Routes tests...${NC}"
if npm run test:e2e -- predictions-routes.spec.ts --project=chromium; then
    echo -e "${GREEN}✅ Predictions & Routes tests passed${NC}"
else
    echo -e "${RED}❌ Predictions & Routes tests failed${NC}"
    test_failed=true
fi

# Offline and error handling tests
echo -e "\n${YELLOW}Running Offline & Error Handling tests...${NC}"
if npm run test:e2e -- offline-error-handling.spec.ts --project=chromium; then
    echo -e "${GREEN}✅ Offline & Error Handling tests passed${NC}"
else
    echo -e "${RED}❌ Offline & Error Handling tests failed${NC}"
    test_failed=true
fi

# Summary
echo -e "\n================================"
echo "📊 Test Summary"
echo "================================"

if [ "$test_failed" = true ]; then
    echo -e "${RED}❌ Some tests failed. Check the output above for details.${NC}"
    echo -e "\nTo view detailed test report, run:"
    echo "  cd frontend && npm run test:e2e:report"
    exit 1
else
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo -e "\nTo view detailed test report, run:"
    echo "  cd frontend && npm run test:e2e:report"
fi