#!/bin/bash

# Run tests with the mock backend
export VITE_API_URL=http://localhost:3001
export BASE_URL=http://localhost:5173

echo "🧪 Running E2E tests with mock backend..."
echo "Frontend: http://localhost:5173"
echo "Mock Backend: http://localhost:3001"

# Run tests without webServer config
npx playwright test auth.spec.ts --project=chromium --reporter=list --workers=1

echo "✅ Tests completed"