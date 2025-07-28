#!/bin/bash
# Stop services started for E2E tests

set -e

echo "🛑 Stopping E2E test services..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Stop backend
if [ -f .backend.pid ]; then
  BACKEND_PID=$(cat .backend.pid)
  if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${YELLOW}Stopping backend (PID: $BACKEND_PID)...${NC}"
    kill $BACKEND_PID
    echo -e "${GREEN}✓ Backend stopped${NC}"
  else
    echo -e "${YELLOW}Backend already stopped${NC}"
  fi
  rm .backend.pid
else
  echo -e "${YELLOW}No backend PID file found${NC}"
fi

# Stop frontend
if [ -f .frontend.pid ]; then
  FRONTEND_PID=$(cat .frontend.pid)
  if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${YELLOW}Stopping frontend (PID: $FRONTEND_PID)...${NC}"
    kill $FRONTEND_PID
    echo -e "${GREEN}✓ Frontend stopped${NC}"
  else
    echo -e "${YELLOW}Frontend already stopped${NC}"
  fi
  rm .frontend.pid
else
  echo -e "${YELLOW}No frontend PID file found${NC}"
fi

# Additional cleanup - kill any remaining processes on the ports
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo -e "${YELLOW}Cleaning up remaining processes on port 8000...${NC}"
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo -e "${YELLOW}Cleaning up remaining processes on port 5173...${NC}"
  lsof -ti:5173 | xargs kill -9 2>/dev/null || true
fi

echo -e "${GREEN}✅ All E2E test services stopped${NC}"