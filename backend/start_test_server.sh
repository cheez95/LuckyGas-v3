#!/bin/bash
# Start backend server for testing

echo "Starting Lucky Gas Backend Test Server..."

# Set test environment
export ENVIRONMENT=test
export TESTING=true
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/luckygas_test"
export SECRET_KEY="test-secret-key-for-validation-sprint"
export ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES=30

# Disable external services for testing
export DISABLE_GOOGLE_APIS=true
export DISABLE_SMS=true
export DISABLE_EINVOICE=true

# Create test database if needed
echo "Setting up test database..."
createdb luckygas_test 2>/dev/null || echo "Test database already exists"

# Start the server
echo "Starting server on http://localhost:8000"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload