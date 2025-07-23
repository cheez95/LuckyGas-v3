#!/bin/bash
# Fixed test runner with proper Python path handling

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
TEST_TYPE="${1:-all}"
COVERAGE="${2:-false}"

echo -e "${BLUE}🧪 Lucky Gas Test Suite Runner (Fixed)${NC}"
echo -e "Project Root: $PROJECT_ROOT"
echo -e "Test Type: $TEST_TYPE"
echo -e "Coverage: $COVERAGE"
echo ""

# Function to run backend tests with proper Python path
run_backend_tests() {
    echo -e "${YELLOW}Running Backend Tests...${NC}"
    cd "$BACKEND_DIR"
    
    # Set Python path
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    
    if [ "$COVERAGE" = "true" ]; then
        echo -e "${BLUE}Running with coverage...${NC}"
        uv run pytest -v --cov=app --cov-report=html --cov-report=term --tb=short
    else
        uv run pytest -v --tb=short
    fi
    
    echo -e "${GREEN}✓ Backend tests completed${NC}"
}

# Function to run frontend tests
run_frontend_tests() {
    echo -e "${YELLOW}Running Frontend Tests...${NC}"
    cd "$FRONTEND_DIR"
    
    if [ -f "package.json" ]; then
        npm test
        
        if [ "$COVERAGE" = "true" ]; then
            npm run test:coverage || echo "Coverage command not found"
        fi
    else
        echo -e "${RED}Frontend package.json not found${NC}"
    fi
    
    echo -e "${GREEN}✓ Frontend tests completed${NC}"
}

# Function to run security tests
run_security_tests() {
    echo -e "${YELLOW}Running Security Tests...${NC}"
    cd "$BACKEND_DIR"
    
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    
    # Run security-focused tests
    uv run pytest tests/backend/security -v --tb=short
    
    echo -e "${GREEN}✓ Security tests completed${NC}"
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${YELLOW}Running Performance Tests...${NC}"
    
    if ! command -v k6 &> /dev/null; then
        echo -e "${YELLOW}k6 is not installed. Skipping performance tests.${NC}"
        return
    fi
    
    cd "$PROJECT_ROOT/tests/performance/load"
    
    # Run load tests if they exist
    if [ -f "api_load.js" ]; then
        k6 run api_load.js || echo "API load test failed"
    fi
    
    if [ -f "websocket_load.js" ]; then
        k6 run websocket_load.js || echo "WebSocket load test failed"
    fi
    
    echo -e "${GREEN}✓ Performance tests completed${NC}"
}

# Main execution
case "$TEST_TYPE" in
    "all")
        run_backend_tests
        run_frontend_tests
        run_security_tests
        run_performance_tests
        ;;
    "backend")
        run_backend_tests
        ;;
    "frontend")
        run_frontend_tests
        ;;
    "security")
        run_security_tests
        ;;
    "performance")
        run_performance_tests
        ;;
    *)
        echo -e "${RED}Invalid test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: $0 [test-type] [coverage]"
        echo ""
        echo "Test types:"
        echo "  all        - Run all tests"
        echo "  backend    - Run backend tests"
        echo "  frontend   - Run frontend tests"
        echo "  security   - Run security tests"
        echo "  performance - Run performance tests"
        echo ""
        echo "Coverage options:"
        echo "  true/false - Enable/disable coverage reporting"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}🎉 Test execution completed!${NC}"

# Show coverage report location if enabled
if [ "$COVERAGE" = "true" ]; then
    echo ""
    echo -e "${BLUE}Coverage reports available at:${NC}"
    echo "  Backend: $BACKEND_DIR/htmlcov/index.html"
    echo "  Frontend: $FRONTEND_DIR/coverage/index.html"
fi