#!/bin/bash

echo "================================================"
echo "    Lucky Gas Local Development Stack"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Check if ports are available
if check_port 8000; then
    echo "Port 8000 is already in use. Please stop the existing backend service."
    exit 1
fi

# Start Backend
echo "Starting Backend..."
echo "----------------------------------------"
cd backend

# Load environment
if [ -f .env.local ]; then
    echo "Loading environment from .env.local..."
    export $(cat .env.local | grep -v '^#' | xargs)
else
    echo "Creating .env.local..."
    cat > .env.local << 'EOF'
DATABASE_URL=postgresql://luckygas:luckygas123@localhost:5432/luckygas
SECRET_KEY=local-development-secret-key-change-in-production
ENVIRONMENT=development
ADMIN_EMAIL=admin@luckygas.com
ADMIN_PASSWORD=admin-password-2025
EOF
    export $(cat .env.local | grep -v '^#' | xargs)
fi

# Start backend with correct import string
echo "Starting backend server..."
uv run uvicorn app.main_simple:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    > ../backend.log 2>&1 &

BACKEND_PID=$!

# Wait for backend to start
echo -n "Waiting for backend to start"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        echo -e "${GREEN}Backend started successfully!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Check if backend started
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}Backend failed to start! Check backend.log for details${NC}"
    tail -20 ../backend.log
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start Frontend
echo ""
echo "Starting Frontend..."
echo "----------------------------------------"
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Starting frontend server..."
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend
echo -n "Waiting for frontend to start"
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        echo -e "${GREEN}Frontend started successfully!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Display status
echo ""
echo "================================================"
echo -e "    ${GREEN}System is running!${NC}"
echo "================================================"
echo ""
echo "  🌐 Frontend:  http://localhost:5173"
echo "  🔧 Backend:   http://localhost:8000"
echo "  📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "  Login Credentials:"
echo "  📧 Email:     admin@luckygas.com"
echo "  🔑 Password:  admin-password-2025"
echo ""
echo "  Press Ctrl+C to stop all services"
echo "================================================"

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $FRONTEND_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    echo "Services stopped"
    exit 0
}

# Set up trap for Ctrl+C
trap cleanup INT

# Keep script running
wait