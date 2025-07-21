#!/bin/bash

# Lucky Gas E2E Test Suite Runner
# This script runs all E2E tests without requiring Google APIs

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Lucky Gas E2E Test Suite - Testing All Web Functions Without Google APIs"
echo "=========================================================================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Function to check if services are running
check_services() {
    echo -e "${YELLOW}Checking if services are running...${NC}"
    
    # Check if backend is running
    if ! curl -s http://localhost:8000/health > /dev/null; then
        echo -e "${RED}Backend is not running. Starting services...${NC}"
        ./deploy.sh up -d
        echo "Waiting for services to be ready..."
        sleep 10
    fi
    
    # Check if frontend is running
    if ! curl -s http://localhost:5173 > /dev/null; then
        echo -e "${RED}Frontend is not running. Starting frontend...${NC}"
        cd frontend && npm run dev &
        FRONTEND_PID=$!
        sleep 5
    fi
    
    echo -e "${GREEN}Services are ready!${NC}"
}

# Function to setup test environment
setup_test_env() {
    echo -e "${YELLOW}Setting up test environment...${NC}"
    
    # Set environment variables to use placeholder services
    export GOOGLE_CLOUD_PROJECT=""
    export VERTEX_AI_LOCATION=""
    export GOOGLE_APPLICATION_CREDENTIALS=""
    
    # Create test data if needed
    if [ "$1" == "--seed" ]; then
        echo "Seeding test data..."
        cd backend
        python -m scripts.seed_test_data
        cd ..
    fi
    
    echo -e "${GREEN}Test environment ready!${NC}"
}

# Function to run specific test suite
run_test_suite() {
    local suite=$1
    local description=$2
    
    echo -e "\n${YELLOW}Running $description...${NC}"
    cd frontend
    
    if npm run test:e2e -- $suite; then
        echo -e "${GREEN}✅ $description passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ $description failed!${NC}"
        return 1
    fi
}

# Function to run all tests
run_all_tests() {
    local failed_tests=()
    
    # Run each test suite
    if ! run_test_suite "auth.spec.ts" "Authentication Tests"; then
        failed_tests+=("Authentication")
    fi
    
    if ! run_test_suite "driver-mobile.spec.ts" "Driver Mobile Interface Tests"; then
        failed_tests+=("Driver Mobile")
    fi
    
    if ! run_test_suite "predictions-routes.spec.ts" "Predictions & Routes Tests (No Google APIs)"; then
        failed_tests+=("Predictions & Routes")
    fi
    
    if ! run_test_suite "offline-error-handling.spec.ts" "Offline & Error Handling Tests"; then
        failed_tests+=("Offline & Error Handling")
    fi
    
    # Additional test suites that exist
    if [ -f "e2e/customer.spec.ts" ]; then
        if ! run_test_suite "customer.spec.ts" "Customer Management Tests"; then
            failed_tests+=("Customer Management")
        fi
    fi
    
    if [ -f "e2e/mobile.spec.ts" ]; then
        if ! run_test_suite "mobile.spec.ts" "Mobile Responsiveness Tests"; then
            failed_tests+=("Mobile Responsiveness")
        fi
    fi
    
    if [ -f "e2e/localization.spec.ts" ]; then
        if ! run_test_suite "localization.spec.ts" "Traditional Chinese Localization Tests"; then
            failed_tests+=("Localization")
        fi
    fi
    
    # Return to root directory
    cd ..
    
    # Summary
    echo -e "\n=========================================="
    echo "📊 Test Summary"
    echo "=========================================="
    
    if [ ${#failed_tests[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed test suites:${NC}"
        for test in "${failed_tests[@]}"; do
            echo "   - $test"
        done
        return 1
    fi
}

# Function to run tests in specific mode
run_mode_tests() {
    local mode=$1
    
    case $mode in
        "mobile")
            echo "Running mobile-specific tests..."
            run_test_suite "driver-mobile.spec.ts --project='Mobile Chrome' --project='Mobile Safari'" "Mobile Tests"
            ;;
        "offline")
            echo "Running offline functionality tests..."
            run_test_suite "offline-error-handling.spec.ts" "Offline Tests"
            ;;
        "no-google")
            echo "Running tests without Google APIs..."
            run_test_suite "predictions-routes.spec.ts" "No Google API Tests"
            ;;
        "headed")
            echo "Running tests in headed mode..."
            cd frontend && npm run test:e2e:headed
            ;;
        "debug")
            echo "Running tests in debug mode..."
            cd frontend && npm run test:e2e:debug
            ;;
        *)
            echo -e "${RED}Unknown mode: $mode${NC}"
            exit 1
            ;;
    esac
}

# Function to generate test report
generate_report() {
    echo -e "\n${YELLOW}Generating test report...${NC}"
    cd frontend
    npm run test:e2e:report
    echo -e "${GREEN}Report generated! View at: frontend/playwright-report/index.html${NC}"
    cd ..
}

# Main execution
main() {
    local mode=""
    local seed_data=false
    local generate_report=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mode)
                mode="$2"
                shift 2
                ;;
            --seed)
                seed_data=true
                shift
                ;;
            --report)
                generate_report=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --mode <mode>    Run specific test mode (mobile|offline|no-google|headed|debug)"
                echo "  --seed           Seed test data before running tests"
                echo "  --report         Generate HTML report after tests"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
        esac
    done
    
    # Check Node.js and npm
    if ! command -v node &> /dev/null; then
        echo -e "${RED}Node.js is not installed${NC}"
        exit 1
    fi
    
    # Install Playwright browsers if needed
    if [ ! -d "frontend/node_modules/@playwright/test/.local-browsers" ]; then
        echo -e "${YELLOW}Installing Playwright browsers...${NC}"
        cd frontend && npx playwright install && cd ..
    fi
    
    # Setup
    check_services
    setup_test_env $([ "$seed_data" = true ] && echo "--seed")
    
    # Run tests
    if [ -n "$mode" ]; then
        run_mode_tests "$mode"
    else
        run_all_tests
    fi
    
    local test_result=$?
    
    # Generate report if requested
    if [ "$generate_report" = true ]; then
        generate_report
    fi
    
    # Cleanup
    if [ -n "$FRONTEND_PID" ]; then
        echo -e "\n${YELLOW}Stopping frontend dev server...${NC}"
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    exit $test_result
}

# Run main function
main "$@"