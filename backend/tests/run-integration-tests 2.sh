#!/bin/bash

# Run Lucky Gas Integration Tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🧪 Running Lucky Gas Integration Tests..."
echo "========================================="

# Check if test environment is running
if ! docker-compose -f docker-compose.test.yml ps | grep -q "postgres-test.*Up.*healthy"; then
    echo "❌ Test environment is not running. Starting it now..."
    ./start-test-env.sh
fi

# Export test environment variables
if [ -f ".env.test" ]; then
    export $(cat .env.test | grep -v '^#' | xargs)
fi

# Set Python path
export PYTHONPATH="${SCRIPT_DIR}/..:$PYTHONPATH"

# Run different test suites
echo ""
echo "1️⃣ Running unit tests..."
echo "------------------------"
pytest unit/ -v --tb=short || true

echo ""
echo "2️⃣ Running integration tests..."
echo "------------------------------"
pytest integration/ -v --tb=short || true

echo ""
echo "3️⃣ Running API tests..."
echo "----------------------"
pytest api/ -v --tb=short || true

echo ""
echo "4️⃣ Running service tests..."
echo "--------------------------"
pytest services/ -v --tb=short || true

echo ""
echo "5️⃣ Running E2E tests..."
echo "----------------------"
pytest e2e/ -v --tb=short --maxfail=3 || true

# Generate test report
echo ""
echo "📊 Generating test report..."
pytest --html=test-report.html --self-contained-html \
       --cov=app --cov-report=html --cov-report=term \
       unit/ integration/ api/ services/ -v || true

echo ""
echo "✅ Integration tests completed!"
echo "========================================="
echo "📍 Test Reports:"
echo "  - HTML Report: ${SCRIPT_DIR}/test-report.html"
echo "  - Coverage Report: ${SCRIPT_DIR}/htmlcov/index.html"
echo "========================================="