#!/bin/bash

echo "==================================================="
echo "LuckyGas E2E Test Validation Suite"
echo "==================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Install dependencies
echo "📦 Installing dependencies..."
cd /Users/lgee258/Desktop/LuckyGas-v3/playwright-tests
npm install

# Install browsers
echo "🌐 Installing browsers..."
npx playwright install

# Set test environment variables
export BASE_URL="http://localhost:3001"
export API_BASE_URL="http://localhost:8000"

# Create reports directory
mkdir -p reports

# Run all tests
echo ""
echo "🧪 Running all E2E tests..."
echo "==================================================="

# Run tests with detailed reporting
npx playwright test --reporter=list,html,json --output=reports

# Check test results
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    TEST_STATUS="PASSED"
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    TEST_STATUS="FAILED"
fi

# Generate summary
echo ""
echo "📊 Generating test summary..."

# Count test results
TOTAL_TESTS=$(find tests -name "*.spec.ts" | wc -l)
echo "Total test files: $TOTAL_TESTS"

# Display individual test results
echo ""
echo "Test Results by Category:"
echo "-------------------------"

for test_file in tests/*.spec.ts; do
    test_name=$(basename "$test_file" .spec.ts)
    echo "- $test_name"
done

echo ""
echo "==================================================="
echo "Test validation complete!"
echo "View detailed report: npx playwright show-report"
echo "==================================================="