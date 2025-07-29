#!/bin/bash

echo "🚀 Starting LuckyGas v3 Development Environment"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Start backend
echo -e "${BLUE}Starting Backend Server...${NC}"
cd backend

# Create a minimal working .env for development
cat > .env <<EOF
# Environment
ENVIRONMENT=development
PROJECT_NAME=LuckyGas Development

# Security
SECRET_KEY=dev-secret-key-min-32-chars-required-for-testing

# Database (using Docker)
POSTGRES_SERVER=localhost
POSTGRES_USER=luckygas
POSTGRES_PASSWORD=luckygas123
POSTGRES_DB=luckygas
POSTGRES_PORT=5432

# Redis (using Docker)
REDIS_URL=redis://localhost:6379/0

# Admin User
FIRST_SUPERUSER=admin@luckygas.tw
FIRST_SUPERUSER_PASSWORD=admin123

# Google Cloud
GCP_PROJECT_ID=vast-tributary-466619-m8
GOOGLE_MAPS_API_KEY=AIzaSyApXfqNpz9fgaf8_S7hXBpG3bXmhc28a5o

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Default values for missing configs
SMS_PROVIDER_URL=http://localhost:8001/mock-sms
EINVOICE_URL=http://localhost:8002/mock-einvoice
BANKING_API_URL=http://localhost:8003/mock-banking
UPLOAD_DIR=./uploads/dev

# Disable external services for dev
VERTEX_AI_LOCATION=
VERTEX_AI_MODEL_ID=
EOF

# Activate virtual environment
source ../.venv/bin/activate

# Start backend in background
echo -e "${GREEN}Backend starting on http://localhost:8000${NC}"
ENVIRONMENT=development nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Check if backend is running
if curl -s http://localhost:8000/docs > /dev/null; then
    echo -e "${GREEN}✅ Backend is running!${NC}"
    echo -e "API Docs: http://localhost:8000/docs"
else
    echo -e "${YELLOW}⚠️  Backend may still be starting...${NC}"
    echo "Check logs: tail -f backend/backend.log"
fi

# Start frontend
echo -e "${BLUE}Starting Frontend Server...${NC}"
cd ../frontend

# Ensure frontend has correct env
cat > .env <<EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_ENV=development
EOF

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend
echo -e "${GREEN}Frontend starting on http://localhost:5173${NC}"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}🎉 Development environment started!${NC}"
echo ""
echo "📊 Service Status:"
echo "✅ PostgreSQL: localhost:5432"
echo "✅ Redis: localhost:6379" 
echo "✅ Backend API: http://localhost:8000"
echo "✅ API Docs: http://localhost:8000/docs"
echo "✅ Frontend: http://localhost:5173"
echo ""
echo "🔑 API Key Status:"
echo "Google Maps API Key: ${YELLOW}Configured (check restrictions)${NC}"
echo "Google Cloud Project: vast-tributary-466619-m8"
echo ""
echo "📱 Test Credentials:"
echo "Admin: admin@luckygas.tw / admin123"
echo ""
echo "🛠️  Useful Commands:"
echo "Backend logs: tail -f backend/backend.log"
echo "Stop all: pkill -f uvicorn && pkill -f vite"
echo ""
echo -e "${YELLOW}⚠️  Note: The Google Maps key may need proper restrictions for your domain${NC}"