#!/bin/bash
# Start services for E2E tests with proper environment setup

set -e

echo "🚀 Starting services for E2E tests..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
  local port=$1
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}

# Function to wait for a service to be ready
wait_for_service() {
  local service_name=$1
  local url=$2
  local max_attempts=60  # Increased for slower systems
  local attempt=0
  
  echo -e "${YELLOW}Waiting for $service_name to be ready at $url...${NC}"
  
  while [ $attempt -lt $max_attempts ]; do
    # Try to connect with a longer timeout
    local response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>&1 || echo "000")
    
    if [[ "$response" =~ ^(200|201|204|301|302|304|401|403|404)$ ]]; then
      echo -e "\n${GREEN}✓ $service_name is ready (HTTP $response)${NC}"
      return 0
    fi
    
    attempt=$((attempt + 1))
    
    # Show progress with more detail
    if [ $((attempt % 10)) -eq 0 ]; then
      echo -e "\n  Still waiting... (attempt $attempt/$max_attempts)"
    else
      echo -n "."
    fi
    
    sleep 2
  done
  
  echo -e "\n${RED}✗ $service_name failed to start after $max_attempts attempts${NC}"
  
  # Show logs for debugging
  if [ "$service_name" == "Backend" ]; then
    echo "Last 20 lines of backend log:"
    tail -20 logs/backend.log 2>/dev/null || echo "No backend log found"
  elif [ "$service_name" == "Frontend" ]; then
    echo "Last 20 lines of frontend log:"
    tail -20 logs/frontend.log 2>/dev/null || echo "No frontend log found"
  fi
  
  return 1
}

# Kill any existing services
echo "Stopping any existing services..."

# Stop any processes from previous runs
if [ -f .backend.pid ]; then
  OLD_BACKEND_PID=$(cat .backend.pid)
  if kill -0 $OLD_BACKEND_PID 2>/dev/null; then
    echo "Stopping old backend process (PID: $OLD_BACKEND_PID)..."
    kill -9 $OLD_BACKEND_PID 2>/dev/null || true
  fi
  rm .backend.pid
fi

if [ -f .frontend.pid ]; then
  OLD_FRONTEND_PID=$(cat .frontend.pid)
  if kill -0 $OLD_FRONTEND_PID 2>/dev/null; then
    echo "Stopping old frontend process (PID: $OLD_FRONTEND_PID)..."
    kill -9 $OLD_FRONTEND_PID 2>/dev/null || true
  fi
  rm .frontend.pid
fi

# Also check ports
if check_port 8000; then
  echo "Stopping processes on port 8000..."
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi
if check_port 5173; then
  echo "Stopping processes on port 5173..."
  lsof -ti:5173 | xargs kill -9 2>/dev/null || true
fi

# Wait for ports to be released
sleep 2

# Set up environment variables
export TESTING=1
export DATABASE_URL=${TEST_DATABASE_URL:-"postgresql://test:test@localhost:5432/luckygas_test"}
export REDIS_URL=${TEST_REDIS_URL:-"redis://localhost:6379"}
export JWT_SECRET_KEY="test-secret-key-for-e2e-tests"
export VITE_API_URL="http://localhost:8000"
export NODE_ENV="test"
export VITE_APP_ENV="test"

# Backend specific
export BACKEND_CORS_ORIGINS='["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]'
export LOG_LEVEL="debug"

# Create log directory
mkdir -p logs

# Start backend
echo -e "${YELLOW}Starting backend service...${NC}"
cd ../../backend

# Ensure virtual environment is set up
if [ ! -d ".venv" ]; then
  echo "Setting up backend virtual environment..."
  uv venv
fi

# Install dependencies if needed
if [ ! -f ".venv/bin/uvicorn" ] && [ ! -f ".venv/Scripts/uvicorn.exe" ]; then
  echo "Installing backend dependencies..."
  uv pip install -r requirements.txt
fi

uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug > ../tests/e2e/logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Start frontend
echo -e "${YELLOW}Starting frontend service...${NC}"
cd ../frontend

# Ensure node_modules exist
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

# Start with explicit port and host
VITE_API_URL="http://localhost:8000" npm run dev -- --port 5173 --host 0.0.0.0 > ../tests/e2e/logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Save PIDs for cleanup
cd ../tests/e2e
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

# Give services a moment to initialize
sleep 3

# Wait for services to be ready
BACKEND_READY=false
FRONTEND_READY=false

if wait_for_service "Backend" "http://localhost:8000/api/v1/health"; then
  BACKEND_READY=true
fi

if wait_for_service "Frontend" "http://localhost:5173"; then
  FRONTEND_READY=true
fi

# Check final status
if [ "$BACKEND_READY" = true ] && [ "$FRONTEND_READY" = true ]; then
  echo -e "${GREEN}✅ All services are ready for E2E tests${NC}"
  echo ""
  echo "Backend logs: tests/e2e/logs/backend.log"
  echo "Frontend logs: tests/e2e/logs/frontend.log"
  echo ""
  echo "To stop services, run: ./stop-services.sh"
  exit 0
else
  echo -e "${RED}❌ Failed to start all services${NC}"
  
  # Clean up
  if [ -n "$BACKEND_PID" ]; then
    kill -9 $BACKEND_PID 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill -9 $FRONTEND_PID 2>/dev/null || true
  fi
  
  rm -f .backend.pid .frontend.pid
  exit 1
fi