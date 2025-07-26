#!/bin/bash

# Minimal test runner - assumes services are already running
echo "🧪 Running minimal E2E tests..."
echo "=============================="

# Check if services are available
echo -n "Checking backend (http://localhost:8000)... "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "000"; then
    echo "❌ Not available"
    echo "Please start the backend: cd backend && uv run uvicorn app.main:app"
    exit 1
else
    echo "✅ Available"
fi

echo -n "Checking frontend (http://localhost:3000)... "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ | grep -q "000"; then
    echo "❌ Not available"
    echo "Please start the frontend: cd frontend && npm run dev"
    exit 1
else
    echo "✅ Available"
fi

# Run smoke tests only
cd "$(dirname "$0")"
npx playwright test specs/smoke.spec.ts --reporter=list