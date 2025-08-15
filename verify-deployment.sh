#!/bin/bash

echo "🔍 Verifying Lucky Gas Deployment..."
echo "====================================="

# Get the backend URL
BACKEND_URL="https://luckygas-backend-154687573210.asia-east1.run.app"
FRONTEND_URL="https://vast-tributary-466619-m8.web.app"

echo "📍 Backend URL: $BACKEND_URL"
echo "📍 Frontend URL: $FRONTEND_URL"
echo ""

# Test backend health
echo "🏥 Testing backend health..."
curl -s "$BACKEND_URL/health" | jq . || echo "❌ Backend health check failed"
echo ""

# Test API health
echo "🏥 Testing API health..."
curl -s "$BACKEND_URL/api/v1/health" | jq . || echo "❌ API health check failed"
echo ""

# Test CORS
echo "🔒 Testing CORS from Firebase domain..."
curl -H "Origin: $FRONTEND_URL" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     -v "$BACKEND_URL/api/v1/health" 2>&1 | grep -i "access-control-allow-origin" || echo "❌ CORS check failed"
echo ""

# Test login endpoint
echo "🔑 Testing login endpoint..."
response=$(curl -X POST "$BACKEND_URL/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -H "Origin: $FRONTEND_URL" \
     -d "username=admin@luckygas.com&password=admin-password-2025" \
     -s)

if echo "$response" | jq -e '.access_token' > /dev/null 2>&1; then
    echo "✅ Login successful!"
    echo "$response" | jq '{ token: .access_token[:20], user: .user }'
else
    echo "❌ Login failed!"
    echo "$response" | jq .
fi
echo ""

# Test frontend
echo "🌐 Testing frontend availability..."
http_code=$(curl -o /dev/null -s -w "%{http_code}\n" "$FRONTEND_URL")
if [ "$http_code" = "200" ]; then
    echo "✅ Frontend is accessible (HTTP $http_code)"
else
    echo "❌ Frontend returned HTTP $http_code"
fi
echo ""

# Test frontend API configuration
echo "🔗 Testing frontend API configuration..."
echo "Checking if frontend contains correct backend URL..."
curl -s "$FRONTEND_URL" | grep -q "$BACKEND_URL" && echo "✅ Frontend configured with correct backend URL" || echo "⚠️  Frontend may not have the correct backend URL"
echo ""

echo "====================================="
echo "📊 Deployment Summary:"
echo "- Backend: $BACKEND_URL"
echo "- Frontend: $FRONTEND_URL"
echo "- Region: asia-east1"
echo "- Login: admin@luckygas.com / admin-password-2025"
echo "====================================="