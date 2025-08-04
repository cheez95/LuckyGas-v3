#!/bin/bash

# Lucky Gas Backend Test Runner
# 
# This script runs all backend tests with proper setup and teardown

set -e

echo "🧪 Lucky Gas Backend Test Suite"
echo "=============================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check prerequisites
check_prerequisites() {
    echo "📋 Checking prerequisites..."
    
    # Check Python
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ Python is not installed${NC}"
        exit 1
    fi
    
    # Check uv
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}❌ uv is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        echo -e "${YELLOW}⚠️  PostgreSQL client not found. Tests may fail if test database is not accessible.${NC}"
    fi
    
    # Check Redis
    if ! command -v redis-cli &> /dev/null; then
        echo -e "${YELLOW}⚠️  Redis client not found. Tests may fail if Redis is not running.${NC}"
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
    echo ""
}

# Function to setup test environment
setup_test_env() {
    echo "🔧 Setting up test environment..."
    
    # Create test database if it doesn't exist
    if command -v psql &> /dev/null; then
        echo "Creating test database..."
        psql -U postgres -c "CREATE DATABASE luckygas_test;" 2>/dev/null || echo "Test database already exists"
    fi
    
    # Install dependencies
    echo "Installing dependencies..."
    uv pip install -r requirements.txt
    uv pip install pytest pytest-asyncio pytest-cov pytest-env httpx
    
    # Run migrations on test database
    echo "Running migrations on test database..."
    export DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/luckygas_test"
    uv run alembic upgrade head || echo -e "${YELLOW}⚠️  Migration failed, continuing anyway${NC}"
    
    echo -e "${GREEN}✅ Test environment ready${NC}"
    echo ""
}

# Function to run specific test category
run_test_category() {
    local category=$1
    local marker=$2
    
    echo -e "${BLUE}🏃 Running ${category} tests...${NC}"
    uv run pytest -m "${marker}" --tb=short -v
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${category} tests passed${NC}"
    else
        echo -e "${RED}❌ ${category} tests failed${NC}"
        return 1
    fi
    echo ""
}

# Parse command line arguments
TEST_TYPE=${1:-"all"}
COVERAGE=${2:-"yes"}

# Check prerequisites
check_prerequisites

# Setup test environment
setup_test_env

# Export test environment variables
export TESTING=1
export ENVIRONMENT=test
export LOG_LEVEL=DEBUG

echo "🚀 Starting test execution..."
echo ""

# Run tests based on type
case $TEST_TYPE in
    "unit")
        run_test_category "Unit" "unit"
        ;;
    "integration")
        run_test_category "Integration" "integration"
        ;;
    "e2e")
        run_test_category "End-to-End" "e2e"
        ;;
    "auth")
        echo -e "${BLUE}🏃 Running authentication tests...${NC}"
        uv run pytest tests/test_api_auth.py -v
        ;;
    "customers")
        echo -e "${BLUE}🏃 Running customer tests...${NC}"
        uv run pytest tests/test_api_customers.py -v
        ;;
    "orders")
        echo -e "${BLUE}🏃 Running order tests...${NC}"
        uv run pytest tests/test_api_orders.py -v
        ;;
    "routes")
        echo -e "${BLUE}🏃 Running route tests...${NC}"
        uv run pytest tests/test_api_routes.py -v
        ;;
    "predictions")
        echo -e "${BLUE}🏃 Running prediction tests...${NC}"
        uv run pytest tests/test_api_predictions.py -v
        ;;
    "all")
        echo -e "${BLUE}🏃 Running all tests...${NC}"
        if [ "$COVERAGE" == "yes" ]; then
            uv run pytest --cov=app --cov-report=html --cov-report=term-missing -v
        else
            uv run pytest -v
        fi
        ;;
    *)
        echo -e "${RED}❌ Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: $0 [unit|integration|e2e|auth|customers|orders|routes|predictions|all] [yes|no]"
        echo "  First argument: test type (default: all)"
        echo "  Second argument: generate coverage report (default: yes)"
        exit 1
        ;;
esac

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    
    # Show coverage report location if generated
    if [ "$COVERAGE" == "yes" ] && [ "$TEST_TYPE" == "all" ]; then
        echo ""
        echo "📊 Coverage report generated:"
        echo "   - Terminal: See output above"
        echo "   - HTML: Open htmlcov/index.html in your browser"
    fi
else
    echo ""
    echo -e "${RED}❌ Some tests failed. Please check the output above.${NC}"
    exit 1
fi

echo ""
echo "🎉 Test run complete!"