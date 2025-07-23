#!/bin/bash
# Lucky Gas Comprehensive Test Runner

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

echo -e "${BLUE}🧪 Lucky Gas Test Suite Runner${NC}"
echo -e "Project Root: $PROJECT_ROOT"
echo -e "Test Type: $TEST_TYPE"
echo -e "Coverage: $COVERAGE"
echo ""

# Function to run backend tests
run_backend_tests() {
    echo -e "${YELLOW}Running Backend Tests...${NC}"
    cd "$BACKEND_DIR"
    
    # Set Python path
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    
    if [ "$COVERAGE" = "true" ]; then
        echo -e "${BLUE}Running with coverage...${NC}"
        uv run pytest -v --cov=app --cov-report=html --cov-report=term
    else
        uv run pytest -v
    fi
    
    echo -e "${GREEN}✓ Backend tests completed${NC}"
}

# Function to run backend unit tests only
run_backend_unit_tests() {
    echo -e "${YELLOW}Running Backend Unit Tests...${NC}"
    cd "$BACKEND_DIR"
    
    # Set Python path
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    
    if [ "$COVERAGE" = "true" ]; then
        uv run pytest tests/unit -v --cov=app --cov-report=html
    else
        uv run pytest tests/unit -v
    fi
    
    echo -e "${GREEN}✓ Backend unit tests completed${NC}"
}

# Function to run backend integration tests
run_backend_integration_tests() {
    echo -e "${YELLOW}Running Backend Integration Tests...${NC}"
    cd "$BACKEND_DIR"
    
    # Set Python path
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    
    uv run pytest tests/integration -v
    
    echo -e "${GREEN}✓ Backend integration tests completed${NC}"
}

# Function to run frontend tests
run_frontend_tests() {
    echo -e "${YELLOW}Running Frontend Tests...${NC}"
    cd "$FRONTEND_DIR"
    
    npm run test
    
    if [ "$COVERAGE" = "true" ]; then
        npm run test:coverage
    fi
    
    echo -e "${GREEN}✓ Frontend tests completed${NC}"
}

# Function to run E2E tests
run_e2e_tests() {
    echo -e "${YELLOW}Running E2E Tests...${NC}"
    cd "$FRONTEND_DIR"
    
    # Start the application in test mode
    echo -e "${BLUE}Starting test servers...${NC}"
    
    # Start backend in background
    cd "$BACKEND_DIR"
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    ENVIRONMENT=test uv run uvicorn app.main:app --port 8000 &
    BACKEND_PID=$!
    
    # Start frontend in background
    cd "$FRONTEND_DIR"
    npm run dev -- --port 3000 &
    FRONTEND_PID=$!
    
    # Wait for servers to start
    sleep 10
    
    # Run E2E tests
    npm run test:e2e
    
    # Cleanup
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    
    echo -e "${GREEN}✓ E2E tests completed${NC}"
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${YELLOW}Running Performance Tests...${NC}"
    
    if ! command -v k6 &> /dev/null; then
        echo -e "${RED}k6 is not installed. Please install it first.${NC}"
        echo "brew install k6  # macOS"
        echo "or visit: https://k6.io/docs/getting-started/installation/"
        exit 1
    fi
    
    cd "$PROJECT_ROOT/tests/performance"
    
    # Run load tests
    k6 run load/api_load.js
    k6 run load/websocket_load.js
    
    echo -e "${GREEN}✓ Performance tests completed${NC}"
}

# Function to run security tests
run_security_tests() {
    echo -e "${YELLOW}Running Security Tests...${NC}"
    cd "$BACKEND_DIR"
    
    # Set Python path
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    
    # Run security-focused tests
    uv run pytest tests/security -v
    
    # Run bandit for Python security issues
    if command -v bandit &> /dev/null; then
        bandit -r app/
    fi
    
    # Run safety check for dependencies
    if command -v safety &> /dev/null; then
        safety check
    fi
    
    echo -e "${GREEN}✓ Security tests completed${NC}"
}

# Function to run specific test file
run_specific_test() {
    local test_path=$1
    echo -e "${YELLOW}Running specific test: $test_path${NC}"
    
    if [[ $test_path == *.py ]]; then
        cd "$BACKEND_DIR"
        export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
        uv run pytest "$test_path" -v
    elif [[ $test_path == *.ts ]] || [[ $test_path == *.tsx ]]; then
        cd "$FRONTEND_DIR"
        npm run test "$test_path"
    else
        echo -e "${RED}Unknown test file type${NC}"
        exit 1
    fi
}

# Function to generate test report
generate_test_report() {
    echo -e "${YELLOW}Generating Test Report...${NC}"
    
    REPORT_DIR="$PROJECT_ROOT/test-reports"
    mkdir -p "$REPORT_DIR"
    
    # Generate timestamp
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    REPORT_FILE="$REPORT_DIR/test_report_$TIMESTAMP.md"
    
    cat > "$REPORT_FILE" << EOF
# Lucky Gas Test Report
Generated: $(date)

## Test Execution Summary

### Backend Tests
EOF
    
    # Run backend tests with report
    cd "$BACKEND_DIR"
    export PYTHONPATH="$BACKEND_DIR:${PYTHONPATH:-}"
    uv run pytest --tb=short --junit-xml="$REPORT_DIR/backend_junit.xml" | tee -a "$REPORT_FILE"
    
    cat >> "$REPORT_FILE" << EOF

### Frontend Tests
EOF
    
    # Run frontend tests with report
    cd "$FRONTEND_DIR"
    npm run test -- --reporter=json > "$REPORT_DIR/frontend_results.json"
    
    echo -e "${GREEN}✓ Test report generated: $REPORT_FILE${NC}"
}

# Main execution
case "$TEST_TYPE" in
    "all")
        run_backend_tests
        run_frontend_tests
        run_e2e_tests
        ;;
    "backend")
        run_backend_tests
        ;;
    "backend-unit")
        run_backend_unit_tests
        ;;
    "backend-integration")
        run_backend_integration_tests
        ;;
    "frontend")
        run_frontend_tests
        ;;
    "e2e")
        run_e2e_tests
        ;;
    "performance")
        run_performance_tests
        ;;
    "security")
        run_security_tests
        ;;
    "report")
        generate_test_report
        ;;
    *)
        if [ -f "$TEST_TYPE" ]; then
            run_specific_test "$TEST_TYPE"
        else
            echo -e "${RED}Invalid test type: $TEST_TYPE${NC}"
            echo ""
            echo "Usage: $0 [test-type] [coverage]"
            echo ""
            echo "Test types:"
            echo "  all                 - Run all tests"
            echo "  backend            - Run all backend tests"
            echo "  backend-unit       - Run backend unit tests only"
            echo "  backend-integration - Run backend integration tests"
            echo "  frontend           - Run frontend tests"
            echo "  e2e                - Run end-to-end tests"
            echo "  performance        - Run performance tests"
            echo "  security           - Run security tests"
            echo "  report             - Generate test report"
            echo "  <file-path>        - Run specific test file"
            echo ""
            echo "Coverage options:"
            echo "  true/false         - Enable/disable coverage reporting"
            echo ""
            echo "Examples:"
            echo "  $0 all true        - Run all tests with coverage"
            echo "  $0 backend         - Run backend tests without coverage"
            echo "  $0 tests/unit/test_auth.py - Run specific test file"
            exit 1
        fi
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