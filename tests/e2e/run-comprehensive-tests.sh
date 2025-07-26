#!/bin/bash

# LuckyGas Comprehensive E2E Test Runner
# This script runs all E2E test suites with proper categorization and reporting

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test categories
declare -a TEST_CATEGORIES=(
  "auth"
  "customer-journey"
  "driver-workflow"
  "websocket-realtime"
  "payment-processing"
  "invoice-management"
  "route-optimization"
  "smoke"
  "performance"
  "mobile"
)

# Function to print colored output
print_status() {
  local color=$1
  local message=$2
  echo -e "${color}${message}${NC}"
}

# Function to check if services are running
check_services() {
  print_status $BLUE "🔍 Checking required services..."
  
  # Check backend
  if ! curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status $RED "❌ Backend is not running on port 8000"
    print_status $YELLOW "📝 Start backend with: cd backend && uv run uvicorn app.main:app --reload"
    return 1
  fi
  
  # Check frontend
  if ! curl -s -f http://localhost:5173 > /dev/null 2>&1; then
    print_status $RED "❌ Frontend is not running on port 5173"
    print_status $YELLOW "📝 Start frontend with: cd frontend && npm run dev"
    return 1
  fi
  
  # Check database
  if ! PGPASSWORD=postgres psql -h localhost -U postgres -d luckygas_test -c "SELECT 1" > /dev/null 2>&1; then
    print_status $RED "❌ PostgreSQL is not accessible"
    print_status $YELLOW "📝 Check your database connection"
    return 1
  fi
  
  print_status $GREEN "✅ All services are running"
  return 0
}

# Function to run tests by category
run_test_category() {
  local category=$1
  local start_time=$(date +%s)
  
  print_status $BLUE "\n🧪 Running $category tests..."
  
  case $category in
    "auth")
      npm test -- specs/auth.spec.ts
      ;;
    "customer-journey")
      npm test -- specs/customer-journey.spec.ts
      ;;
    "driver-workflow")
      npm test -- specs/driver-workflow.spec.ts --project="mobile-chrome" --project="mobile-safari"
      ;;
    "websocket-realtime")
      npm test -- specs/websocket-realtime.spec.ts
      ;;
    "payment-processing")
      npm test -- specs/payment-processing.spec.ts
      ;;
    "invoice-management")
      npm test -- specs/invoice-management.spec.ts
      ;;
    "route-optimization")
      npm test -- specs/route-optimization.spec.ts
      ;;
    "smoke")
      npm test -- specs/smoke.spec.ts
      ;;
    "performance")
      npm test -- performance.spec.ts --project=performance
      ;;
    "mobile")
      npm test -- mobile.spec.ts --project="mobile-chrome" --project="mobile-safari"
      ;;
    *)
      print_status $RED "❌ Unknown test category: $category"
      return 1
      ;;
  esac
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  
  if [ $? -eq 0 ]; then
    print_status $GREEN "✅ $category tests completed in ${duration}s"
  else
    print_status $RED "❌ $category tests failed after ${duration}s"
    return 1
  fi
}

# Function to generate test report
generate_report() {
  local report_file="test-results/comprehensive-report-$(date +%Y%m%d-%H%M%S).html"
  
  print_status $BLUE "\n📊 Generating comprehensive test report..."
  
  # Merge all test results
  npx playwright merge-reports --reporter html ./test-results
  
  print_status $GREEN "✅ Report generated: $report_file"
  print_status $YELLOW "📝 View report with: npx playwright show-report"
}

# Main execution
main() {
  print_status $BLUE "🚀 LuckyGas Comprehensive E2E Test Suite"
  print_status $BLUE "========================================\n"
  
  # Parse command line arguments
  if [ $# -eq 0 ]; then
    # Run all tests
    TESTS_TO_RUN=("${TEST_CATEGORIES[@]}")
  else
    TESTS_TO_RUN=("$@")
  fi
  
  # Check services
  if ! check_services; then
    print_status $RED "\n❌ Please start all required services before running tests"
    exit 1
  fi
  
  # Install dependencies if needed
  if [ ! -d "node_modules" ]; then
    print_status $YELLOW "📦 Installing test dependencies..."
    npm install
  fi
  
  # Install browsers if needed
  if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    print_status $YELLOW "🌐 Installing Playwright browsers..."
    npx playwright install --with-deps
  fi
  
  # Clear previous results
  rm -rf test-results playwright-report
  mkdir -p test-results
  
  # Track results
  TOTAL_TESTS=0
  PASSED_TESTS=0
  FAILED_TESTS=0
  declare -a FAILED_CATEGORIES=()
  
  # Run selected test categories
  for category in "${TESTS_TO_RUN[@]}"; do
    if run_test_category "$category"; then
      ((PASSED_TESTS++))
    else
      ((FAILED_TESTS++))
      FAILED_CATEGORIES+=("$category")
    fi
    ((TOTAL_TESTS++))
  done
  
  # Generate report
  generate_report
  
  # Print summary
  print_status $BLUE "\n📊 Test Summary"
  print_status $BLUE "==============="
  echo "Total Categories: $TOTAL_TESTS"
  print_status $GREEN "Passed: $PASSED_TESTS"
  print_status $RED "Failed: $FAILED_TESTS"
  
  if [ ${#FAILED_CATEGORIES[@]} -gt 0 ]; then
    print_status $RED "\nFailed Categories:"
    for category in "${FAILED_CATEGORIES[@]}"; do
      echo "  - $category"
    done
  fi
  
  # Exit with appropriate code
  if [ $FAILED_TESTS -gt 0 ]; then
    print_status $RED "\n❌ Some tests failed. Check the report for details."
    exit 1
  else
    print_status $GREEN "\n✅ All tests passed successfully!"
    exit 0
  fi
}

# Run main function with all arguments
main "$@"