#!/bin/bash

# Start services and run E2E tests
set -e

echo "🚀 Starting LuckyGas services for E2E testing..."
echo "==========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Project root: $PROJECT_ROOT"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Port $port is already in use${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Port $port is not in use${NC}"
        return 1
    fi
}

# Check if services are already running
BACKEND_RUNNING=false
FRONTEND_RUNNING=false

if check_port 8000; then
    BACKEND_RUNNING=true
fi

if check_port 3000; then
    FRONTEND_RUNNING=true
fi

# Start backend if not running
if [ "$BACKEND_RUNNING" = false ]; then
    echo -e "${YELLOW}Starting backend service...${NC}"
    cd "$PROJECT_ROOT/backend"
    
    # Start backend in background
    TESTING=1 DATABASE_URL="${TEST_DATABASE_URL:-postgresql://test:test@localhost:5432/luckygas_test}" \
        nohup uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"
    
    # Wait for backend to start
    echo -n "Waiting for backend to start"
    for i in {1..30}; do
        if check_port 8000 > /dev/null 2>&1; then
            echo -e "\n${GREEN}✅ Backend started successfully${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    if ! check_port 8000 > /dev/null 2>&1; then
        echo -e "\n${RED}❌ Backend failed to start${NC}"
        echo "Backend logs:"
        tail -n 50 backend.log
        exit 1
    fi
else
    echo -e "${GREEN}✅ Backend already running${NC}"
fi

# Start frontend if not running
if [ "$FRONTEND_RUNNING" = false ]; then
    echo -e "${YELLOW}Starting frontend service...${NC}"
    cd "$PROJECT_ROOT/frontend"
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    
    # Start frontend in background
    VITE_API_URL=http://localhost:8000 nohup npm run dev > frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
    
    # Wait for frontend to start
    echo -n "Waiting for frontend to start"
    for i in {1..30}; do
        if check_port 3000 > /dev/null 2>&1; then
            echo -e "\n${GREEN}✅ Frontend started successfully${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    if ! check_port 3000 > /dev/null 2>&1; then
        echo -e "\n${RED}❌ Frontend failed to start${NC}"
        echo "Frontend logs:"
        tail -n 50 frontend.log
        exit 1
    fi
else
    echo -e "${GREEN}✅ Frontend already running${NC}"
fi

# Run tests
echo -e "\n${YELLOW}Running E2E tests...${NC}"
cd "$PROJECT_ROOT/tests/e2e"

# Install test dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing test dependencies..."
    npm install
    npx playwright install --with-deps
fi

# Run tests
npm test

TEST_EXIT_CODE=$?

# Cleanup: Stop services if we started them
if [ "$BACKEND_RUNNING" = false ] && [ ! -z "$BACKEND_PID" ]; then
    echo -e "\n${YELLOW}Stopping backend service...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    
    # Also kill the uvicorn process
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
fi

if [ "$FRONTEND_RUNNING" = false ] && [ ! -z "$FRONTEND_PID" ]; then
    echo -e "\n${YELLOW}Stopping frontend service...${NC}"
    kill $FRONTEND_PID 2>/dev/null || true
    
    # Also kill the vite process
    pkill -f "vite" 2>/dev/null || true
fi

# Exit with test exit code
exit $TEST_EXIT_CODE