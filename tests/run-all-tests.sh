#!/bin/bash
# Comprehensive test runner for Lucky Gas project

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

echo -e "${BLUE}🚀 Lucky Gas Comprehensive Test Suite${NC}"
echo "======================================="
echo "Starting at: $(date)"
echo ""

# Function to run tests and track results
run_test_suite() {
  local suite_name=$1
  local command=$2
  local directory=$3
  
  echo -e "\n${BLUE}Running $suite_name...${NC}"
  
  cd "$directory"
  
  if eval "$command"; then
    echo -e "${GREEN}✓ $suite_name PASSED${NC}"
    ((PASSED_TESTS++))
  else
    echo -e "${RED}✗ $suite_name FAILED${NC}"
    ((FAILED_TESTS++))
  fi
  
  ((TOTAL_TESTS++))
}

# 1. Validate infrastructure first
echo -e "${YELLOW}Step 1: Validating test infrastructure${NC}"
if ./validate-test-infrastructure.sh; then
  echo -e "${GREEN}✓ Infrastructure validation passed${NC}"
else
  echo -e "${RED}✗ Infrastructure validation failed${NC}"
  echo "Please fix infrastructure issues before running tests"
  exit 1
fi

# 2. Run frontend validation
echo -e "\n${YELLOW}Step 2: Frontend validation${NC}"
run_test_suite "Frontend validation" "node scripts/validate-frontend.js" "../frontend"

# 3. Run backend tests
echo -e "\n${YELLOW}Step 3: Backend unit tests${NC}"
run_test_suite "Backend unit tests" "uv run pytest tests/ -v --tb=short" "../backend"

# 4. Run frontend unit tests
echo -e "\n${YELLOW}Step 4: Frontend unit tests${NC}"
run_test_suite "Frontend unit tests" "npm test -- --passWithNoTests" "../frontend"

# 5. Start services for E2E tests
echo -e "\n${YELLOW}Step 5: Starting services for E2E tests${NC}"
cd ../tests/e2e

# Stop any existing services
./stop-services.sh > /dev/null 2>&1 || true

# Start services
echo "Starting backend and frontend services..."
if ./start-services.sh; then
  echo -e "${GREEN}✓ Services started successfully${NC}"
  
  # Give services time to stabilize
  sleep 5
  
  # 6. Run E2E tests
  echo -e "\n${YELLOW}Step 6: E2E tests${NC}"
  
  # Run different E2E test suites
  cd ../..
  
  # Basic auth tests
  echo -e "\n${BLUE}Running authentication tests...${NC}"
  if npx playwright test auth.spec.ts --project=chromium; then
    echo -e "${GREEN}✓ Auth tests PASSED${NC}"
    ((PASSED_TESTS++))
  else
    echo -e "${RED}✗ Auth tests FAILED${NC}"
    ((FAILED_TESTS++))
  fi
  ((TOTAL_TESTS++))
  
  # Customer tests
  echo -e "\n${BLUE}Running customer tests...${NC}"
  if npx playwright test customer.spec.ts --project=chromium; then
    echo -e "${GREEN}✓ Customer tests PASSED${NC}"
    ((PASSED_TESTS++))
  else
    echo -e "${RED}✗ Customer tests FAILED${NC}"
    ((FAILED_TESTS++))
  fi
  ((TOTAL_TESTS++))
  
  # Mobile tests
  echo -e "\n${BLUE}Running mobile tests...${NC}"
  if npx playwright test mobile.spec.ts --project="Mobile Chrome"; then
    echo -e "${GREEN}✓ Mobile tests PASSED${NC}"
    ((PASSED_TESTS++))
  else
    echo -e "${RED}✗ Mobile tests FAILED${NC}"
    ((FAILED_TESTS++))
  fi
  ((TOTAL_TESTS++))
  
  # Visual regression tests (if baselines exist)
  if [ -d "tests/e2e/visual-regression.spec.ts-snapshots" ]; then
    echo -e "\n${BLUE}Running visual regression tests...${NC}"
    if npx playwright test visual-regression.spec.ts --project=chromium; then
      echo -e "${GREEN}✓ Visual tests PASSED${NC}"
      ((PASSED_TESTS++))
    else
      echo -e "${RED}✗ Visual tests FAILED${NC}"
      ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
  else
    echo -e "\n${YELLOW}⚠ Skipping visual tests (no baselines)${NC}"
  fi
  
  # Stop services
  cd tests/e2e
  ./stop-services.sh
  
else
  echo -e "${RED}✗ Failed to start services${NC}"
  echo "Skipping E2E tests"
  ((FAILED_TESTS+=4))
  ((TOTAL_TESTS+=4))
fi

# 7. Generate reports
echo -e "\n${YELLOW}Step 7: Generating test reports${NC}"

# Create test results directory
mkdir -p test-results

# Generate summary report
cat > test-results/test-summary.md << EOF
# Lucky Gas Test Execution Summary

**Date:** $(date)

## Test Results

- **Total Test Suites:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS
- **Failed:** $FAILED_TESTS
- **Success Rate:** $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%

## Test Categories

### Unit Tests
- Backend: $([ -f ../backend/pytest.xml ] && echo "✓ Executed" || echo "✗ Not executed")
- Frontend: $([ -d ../frontend/coverage ] && echo "✓ Executed" || echo "✗ Not executed")

### E2E Tests
- Authentication: $([ -f playwright-report/index.html ] && echo "✓ Executed" || echo "✗ Not executed")
- Customer Management: $([ -f playwright-report/index.html ] && echo "✓ Executed" || echo "✗ Not executed")
- Mobile: $([ -f playwright-report/index.html ] && echo "✓ Executed" || echo "✗ Not executed")
- Visual Regression: $([ -d "tests/e2e/visual-regression.spec.ts-snapshots" ] && echo "✓ Executed" || echo "⚠ Skipped")

## Reports

- Playwright HTML Report: \`npx playwright show-report\`
- Frontend Coverage: \`open frontend/coverage/index.html\`
- Backend Coverage: \`open backend/htmlcov/index.html\`

## Logs

- Backend logs: \`tests/e2e/logs/backend.log\`
- Frontend logs: \`tests/e2e/logs/frontend.log\`
EOF

# Summary
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${BLUE}Test Execution Complete${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "Total test suites: $TOTAL_TESTS"
echo -e "${GREEN}Passed:${NC} $PASSED_TESTS"
echo -e "${RED}Failed:${NC} $FAILED_TESTS"
echo -e "Success rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"

if [ $FAILED_TESTS -eq 0 ]; then
  echo -e "\n${GREEN}🎉 All tests passed!${NC}"
  exit 0
else
  echo -e "\n${RED}❌ Some tests failed${NC}"
  echo "View detailed reports:"
  echo "  - Playwright: npx playwright show-report"
  echo "  - Test summary: test-results/test-summary.md"
  exit 1
fi