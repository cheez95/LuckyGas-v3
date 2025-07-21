#!/bin/bash

# Simple E2E test runner
echo "🚀 Starting E2E tests with mock backend..."

# Start mock backend
echo "📦 Starting mock backend on port 3001..."
node e2e/mock-backend.js &
MOCK_PID=$!

# Wait for mock backend to start
sleep 3

# Start frontend with test environment
echo "🎨 Starting frontend with test environment..."
VITE_API_URL=http://localhost:3001 npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5

# Run tests
echo "🧪 Running E2E tests..."
npx playwright test --project=chromium

# Capture exit code
TEST_EXIT_CODE=$?

# Cleanup
echo "🧹 Cleaning up..."
kill $MOCK_PID $FRONTEND_PID 2>/dev/null

exit $TEST_EXIT_CODE