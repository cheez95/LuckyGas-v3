#!/bin/bash

# Start Lucky Gas Test Environment
# This script starts all test services using docker-compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Lucky Gas Test Environment..."
echo "========================================="

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.test.yml down 2>/dev/null || true

# Remove old volumes (optional, comment out to persist data)
# echo "🗑️  Removing old volumes..."
# docker-compose -f docker-compose.test.yml down -v 2>/dev/null || true

# Start services
echo "🐳 Starting Docker services..."
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."

# Function to check if a service is healthy
check_service() {
    local service=$1
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f docker-compose.test.yml ps | grep -q "$service.*healthy"; then
            echo "✅ $service is healthy"
            return 0
        fi
        
        echo "⏳ Waiting for $service... ($((attempt + 1))/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service failed to become healthy"
    return 1
}

# Check each service
check_service "postgres-test"
check_service "redis-test"
check_service "mock-gcp"
check_service "mock-sms"
check_service "mock-einvoice"
check_service "mock-banking"
check_service "minio-test"

# Run database migrations
echo "🔧 Running database migrations..."
cd ..
if [ -f ".env.test" ]; then
    export $(cat .env.test | grep -v '^#' | xargs)
fi

# Wait a bit more for PostgreSQL to be fully ready
sleep 5

# Run Alembic migrations
echo "📦 Applying database schema..."
cd ..
python -m alembic upgrade head

# Initialize test data
echo "🌱 Initializing test data..."
cd tests
python init_test_data.py

# Display service URLs
echo ""
echo "✅ Test environment is ready!"
echo "========================================="
echo "📍 Service URLs:"
echo "  - API:          http://localhost:8000"
echo "  - PostgreSQL:   localhost:5433"
echo "  - Redis:        localhost:6380"
echo "  - MinIO:        http://localhost:9000 (console: http://localhost:9001)"
echo "  - Mailhog:      http://localhost:8025"
echo "  - Mock GCP:     http://localhost:8080"
echo "  - Mock SMS:     http://localhost:8001"
echo "  - Mock E-Invoice: http://localhost:8002"
echo "  - Mock Banking: http://localhost:8003"
echo ""
echo "🔑 Test Credentials:"
echo "  - DB User:      luckygas_test / test_password_secure_123"
echo "  - MinIO:        minioadmin / minioadmin123"
echo "  - Admin User:   admin@test.luckygas.tw / TestAdmin123!"
echo ""
echo "💡 To stop the environment, run: ./stop-test-env.sh"
echo "💡 To view logs, run: docker-compose -f docker-compose.test.yml logs -f"
echo "========================================="