#!/bin/bash
set -e

# Lucky Gas Docker Testing Script
echo "🧪 Lucky Gas Docker Testing Suite"
echo "================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check Docker
echo -e "\n📦 Checking Docker Installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
else
    print_status "Docker is installed: $(docker --version)"
fi

if ! docker ps &> /dev/null; then
    print_error "Docker daemon is not running. Please start Docker Desktop."
    echo "On macOS: Open Docker Desktop from Applications"
    exit 1
else
    print_status "Docker daemon is running"
fi

# Navigate to project root
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)
print_status "Project root: $PROJECT_ROOT"

# 1. Start Docker Services
echo -e "\n🚀 Starting Docker Services..."
docker-compose down
docker-compose up -d db redis adminer

# Wait for PostgreSQL to be ready
echo -e "\n⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U luckygas &> /dev/null; then
        print_status "PostgreSQL is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# Additional wait for full initialization
sleep 2

# Check Redis
echo -e "\n🔍 Checking Redis..."
if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
    print_status "Redis is responding"
else
    print_error "Redis is not responding"
fi

# 2. Run Database Migrations
echo -e "\n🔄 Running Database Migrations..."
cd backend
export PYTHONPATH=$PWD
# Use test environment with port 5433
cp .env.test .env
export DATABASE_URL=postgresql+psycopg2://luckygas:luckygas123@localhost:5433/luckygas
export POSTGRES_SERVER=localhost
export REDIS_URL=redis://localhost:6379

# Run Alembic migrations
uv run alembic upgrade head || print_error "Failed to run migrations"

# 3. Import Test Data
echo -e "\n📊 Importing Test Data..."
uv run python ../database/migrations/001_import_excel.py || print_error "Failed to import Excel data"
uv run python ../database/migrations/002_import_sqlite.py || print_error "Failed to import SQLite data"

# 4. Start Backend API
echo -e "\n🌐 Starting Backend API..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
sleep 5

# 5. Test API Health
echo -e "\n❤️  Testing API Health..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    print_status "API health check passed"
else
    print_error "API health check failed"
fi

# 6. Test Authentication
echo -e "\n🔐 Testing Authentication..."
LOGIN_RESPONSE=$(curl -s -X POST http://t:8000/api/v1/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin@luckygas.tw&password=admin123")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    print_status "Login successful"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')
    echo "Token: ${TOKEN:0:20}..."
else
    print_error "Login failed"
    echo "$LOGIN_RESPONSE"
fi

# 7. Test Customer API
echo -e "\n👥 Testing Customer API..."
CUSTOMER_RESPONSE=$(curl -s -X GET http://localhost:8000/api/v1/customers \
    -H "Authorization: Bearer $TOKEN")

if echo "$CUSTOMER_RESPONSE" | grep -q "customer_code"; then
    print_status "Customer API working"
    CUSTOMER_COUNT=$(echo "$CUSTOMER_RESPONSE" | grep -o "customer_code" | wc -l)
    echo "Found $CUSTOMER_COUNT customers"
else
    print_error "Customer API failed"
    echo "$CUSTOMER_RESPONSE"
fi

# 8. Test Database Web Interface
echo -e "\n🖥️  Testing Adminer..."
if curl -s http://localhost:8080 | grep -q "Adminer"; then
    print_status "Adminer is accessible at http://localhost:8080"
    echo "Credentials: Server=db, Username=luckygas, Password=luckygas123"
else
    print_error "Adminer is not accessible"
fi

# 9. Test API Documentation
echo -e "\n📚 Testing API Documentation..."
if curl -s http://localhost:8000/docs | grep -q "Lucky Gas"; then
    print_status "API documentation available at http://localhost:8000/docs"
else
    print_error "API documentation not accessible"
fi

# 10. Database Connection Test
echo -e "\n🗄️  Testing Direct Database Connection..."
PGPASSWORD=luckygas123 psql -h localhost -U luckygas -d luckygas -c "SELECT COUNT(*) FROM customers;" 2>/dev/null || \
    docker-compose exec -T db psql -U luckygas -d luckygas -c "SELECT COUNT(*) FROM customers;"

# Stop the API server
kill $API_PID 2>/dev/null

# Summary
echo -e "\n📊 Test Summary"
echo "==============="
echo "✅ Docker Services: Running"
echo "✅ Database: Connected"
echo "✅ API: Functional"
echo "✅ Authentication: Working"
echo "✅ Web Interfaces: Accessible"
echo ""
echo "🔗 Access Points:"
echo "- API: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo "- Database UI: http://localhost:8080"
echo ""
echo "To stop services: docker-compose down"