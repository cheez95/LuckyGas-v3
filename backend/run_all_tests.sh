#!/bin/bash
# Comprehensive test runner for Lucky Gas v3

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="test_reports_${TIMESTAMP}"
FAILED_TESTS=0

# Create report directory
mkdir -p "${REPORT_DIR}"

echo -e "${BLUE}🚀 Lucky Gas v3 - Comprehensive Test Suite${NC}"
echo -e "${BLUE}===========================================${NC}\n"

# Function to run test suite
run_test_suite() {
    local suite_name=$1
    local test_command=$2
    local report_file="${REPORT_DIR}/${suite_name}_report.json"
    
    echo -e "\n${YELLOW}Running ${suite_name} tests...${NC}"
    
    if eval "${test_command} --json-report --json-report-file=${report_file}"; then
        echo -e "${GREEN}✅ ${suite_name} tests passed${NC}"
    else
        echo -e "${RED}❌ ${suite_name} tests failed${NC}"
        ((FAILED_TESTS++))
    fi
}

# 1. Setup environment
echo -e "${YELLOW}Setting up test environment...${NC}"
if [ -f "./setup_tests.sh" ]; then
    ./setup_tests.sh
else
    echo -e "${RED}❌ setup_tests.sh not found${NC}"
    exit 1
fi

# 2. Validate infrastructure
echo -e "\n${YELLOW}Validating test infrastructure...${NC}"
uv run python tests/validate_test_infrastructure.py

# 3. Run Unit Tests
run_test_suite "unit" "uv run pytest tests -m unit -v"

# 4. Run Integration Tests
run_test_suite "integration" "uv run pytest tests/integration -m integration -v"

# 5. Run E2E Tests
run_test_suite "e2e" "uv run pytest tests/e2e -m e2e -v"

# 6. Run Security Tests
run_test_suite "security" "uv run pytest tests/security -v"

# 7. Run Performance Tests
run_test_suite "performance" "uv run pytest tests/performance -v"

# 8. Run Chaos Engineering Tests (optional - requires special environment)
if [ "$RUN_CHAOS_TESTS" == "true" ]; then
    echo -e "\n${YELLOW}Running Chaos Engineering tests...${NC}"
    cd tests/chaos && python run_chaos_tests.py --output "../../${REPORT_DIR}/chaos"
    cd ../..
else
    echo -e "\n${BLUE}ℹ️  Skipping Chaos tests (set RUN_CHAOS_TESTS=true to enable)${NC}"
fi

# 9. Generate combined report
echo -e "\n${YELLOW}Generating combined test report...${NC}"

cat > "${REPORT_DIR}/COMBINED_TEST_REPORT.md" << EOF
# Lucky Gas v3 - Combined Test Report

**Date**: $(date)
**Environment**: test

## Test Suite Summary

| Suite | Status | Details |
|-------|--------|---------|
| Unit Tests | $([ -f "${REPORT_DIR}/unit_report.json" ] && echo "✅ Passed" || echo "❌ Failed") | See unit_report.json |
| Integration Tests | $([ -f "${REPORT_DIR}/integration_report.json" ] && echo "✅ Passed" || echo "❌ Failed") | See integration_report.json |
| E2E Tests | $([ -f "${REPORT_DIR}/e2e_report.json" ] && echo "✅ Passed" || echo "❌ Failed") | See e2e_report.json |
| Security Tests | $([ -f "${REPORT_DIR}/security_report.json" ] && echo "✅ Passed" || echo "❌ Failed") | See security_report.json |
| Performance Tests | $([ -f "${REPORT_DIR}/performance_report.json" ] && echo "✅ Passed" || echo "❌ Failed") | See performance_report.json |

## Coverage Report

$(uv run pytest --cov=app --cov-report=term 2>/dev/null | tail -n 10)

## Critical Path Tests

The following critical path tests must pass for deployment:
- [ ] User authentication flow
- [ ] Customer creation and management
- [ ] Order creation and processing
- [ ] Payment processing
- [ ] Invoice generation
- [ ] Route optimization
- [ ] Real-time updates via WebSocket

## Next Steps

1. Review failed tests in individual reports
2. Fix any failing tests before deployment
3. Ensure coverage is above 80%
4. Run chaos tests in staging environment
5. Update documentation based on test results

---
Generated on: $(date)
EOF

# 10. Coverage report
echo -e "\n${YELLOW}Generating coverage report...${NC}"
uv run pytest --cov=app --cov-report=html --cov-report=term

# Summary
echo -e "\n${BLUE}======================================${NC}"
echo -e "${BLUE}TEST EXECUTION SUMMARY${NC}"
echo -e "${BLUE}======================================${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ All test suites passed!${NC}"
    echo -e "\nReports generated in: ${REPORT_DIR}/"
    echo -e "Coverage report: htmlcov/index.html"
    exit 0
else
    echo -e "${RED}❌ ${FAILED_TESTS} test suite(s) failed${NC}"
    echo -e "\nReports generated in: ${REPORT_DIR}/"
    echo -e "Please review the failed tests and fix them before deployment."
    exit 1
fi