#!/bin/bash
# Test runner script with proper environment setup

echo "🧪 Running Lucky Gas Backend Tests..."

# Set environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export TESTING=1
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
export SECRET_KEY="test-secret-key"
export ENVIRONMENT="test"

# Create test database if needed
rm -f test.db

# Run specific test suite based on argument
if [ "$1" == "integration" ]; then
    echo "Running integration tests..."
    uv run pytest tests/integration/ -v --tb=short
elif [ "$1" == "analytics" ]; then
    echo "Running analytics integration tests..."
    uv run pytest tests/integration/test_analytics_flow.py -v
elif [ "$1" == "unit" ]; then
    echo "Running unit tests..."
    uv run pytest tests/unit/ -v
else
    echo "Running all tests..."
    uv run pytest -v
fi

# Cleanup
rm -f test.db