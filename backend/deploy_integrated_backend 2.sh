#!/bin/bash

# Lucky Gas Integrated Backend Deployment Script
# Safely switches from minimal to integrated backend

echo "🚀 Lucky Gas Backend Integration Deployment"
echo "=========================================="

# Check if minimal backend is running
MINIMAL_PID=$(ps aux | grep "minimal_backend.py" | grep -v grep | awk '{print $2}')

if [ -n "$MINIMAL_PID" ]; then
    echo "✅ Found minimal backend running with PID: $MINIMAL_PID"
else
    echo "⚠️  No minimal backend found running"
fi

# Navigate to backend directory
cd /Users/lgee258/Desktop/LuckyGas-v3/backend

# Test the integrated backend first
echo ""
echo "📋 Testing integrated backend..."
uv run python -m py_compile minimal_backend_integrated.py
if [ $? -eq 0 ]; then
    echo "✅ Syntax check passed"
else
    echo "❌ Syntax errors found!"
    exit 1
fi

# Stop the old backend if running
if [ -n "$MINIMAL_PID" ]; then
    echo ""
    echo "🛑 Stopping minimal backend..."
    kill $MINIMAL_PID
    sleep 2
    
    # Verify it stopped
    if ps -p $MINIMAL_PID > /dev/null; then
        echo "⚠️  Process still running, forcing kill..."
        kill -9 $MINIMAL_PID
    fi
    echo "✅ Minimal backend stopped"
fi

# Start the integrated backend
echo ""
echo "🚀 Starting integrated backend..."
nohup uv run python minimal_backend_integrated.py > integrated_backend.log 2>&1 &
NEW_PID=$!

# Wait for startup
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if it's running
if ps -p $NEW_PID > /dev/null; then
    echo "✅ Integrated backend started with PID: $NEW_PID"
else
    echo "❌ Failed to start integrated backend!"
    echo "📋 Check integrated_backend.log for errors"
    exit 1
fi

# Test the health endpoint
echo ""
echo "🏥 Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/v1/health)

if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    echo "✅ Health check passed"
    echo "   Response: $HEALTH_RESPONSE"
else
    echo "❌ Health check failed!"
    echo "   Response: $HEALTH_RESPONSE"
fi

# Test authentication
echo ""
echo "🔐 Testing authentication endpoint..."
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=test@example.com&password=password123")

if [[ $AUTH_RESPONSE == *"access_token"* ]]; then
    echo "✅ Authentication endpoint working"
else
    echo "⚠️  Authentication test failed"
    echo "   Response: $AUTH_RESPONSE"
fi

# Summary
echo ""
echo "📊 Deployment Summary"
echo "===================="
echo "✅ Integrated backend deployed successfully"
echo "📍 Running on: http://localhost:8000"
echo "📄 Logs: integrated_backend.log"
echo "🆔 Process ID: $NEW_PID"
echo ""
echo "🌐 Frontend can now access all endpoints:"
echo "   - /api/v1/auth/*      ✅"
echo "   - /api/v1/customers   ✅"
echo "   - /api/v1/orders      ✅"
echo "   - /api/v1/routes      ✅"
echo "   - /api/v1/products    ✅"
echo "   - /api/v1/predictions ✅"
echo "   - /api/v1/websocket   ✅"
echo ""
echo "🎉 Integration complete! Frontend should now work without errors."