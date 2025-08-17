#!/bin/bash

# Lucky Gas System Diagnostic Script
# This script tests all critical endpoints and identifies issues

echo "=========================================="
echo "Lucky Gas System Diagnostic Tool"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# API Configuration
API_BASE="https://luckygas-backend-production-154687573210.asia-east1.run.app/api/v1"
TEST_USER="admin@luckygas.com"
TEST_PASS="admin123"

echo "🔍 Testing Backend API..."
echo "API Base URL: $API_BASE"
echo ""

# Test 1: Check if API is reachable
echo -n "1. Testing API connectivity... "
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/health" 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ] || [ "$HEALTH_RESPONSE" = "404" ]; then
    echo -e "${GREEN}✓ API is reachable (HTTP $HEALTH_RESPONSE)${NC}"
else
    echo -e "${RED}✗ API is not reachable (HTTP $HEALTH_RESPONSE)${NC}"
    echo "   Cannot proceed without API connection"
    exit 1
fi

# Test 2: Test login endpoint
echo ""
echo "2. Testing login endpoint..."
echo "   Username: $TEST_USER"
echo "   Password: [hidden]"

# Create login payload
LOGIN_PAYLOAD=$(cat <<EOF
{
  "username": "$TEST_USER",
  "password": "$TEST_PASS"
}
EOF
)

# Attempt login
echo "   Sending login request..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "$LOGIN_PAYLOAD" 2>/dev/null)

# Check if we got a response
if [ -z "$LOGIN_RESPONSE" ]; then
    echo -e "   ${RED}✗ No response from login endpoint${NC}"
    exit 1
fi

# Parse response
echo "   Response received:"
echo "   $LOGIN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "   $LOGIN_RESPONSE"

# Extract token
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    echo -e "   ${GREEN}✓ Login successful! Token received${NC}"
    echo "   Token (first 20 chars): ${TOKEN:0:20}..."
else
    echo -e "   ${RED}✗ Login failed - no token received${NC}"
    
    # Try alternative login format
    echo ""
    echo "   Trying alternative login format (form data)..."
    LOGIN_FORM="username=$TEST_USER&password=$TEST_PASS"
    LOGIN_RESPONSE2=$(curl -s -X POST "$API_BASE/auth/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "$LOGIN_FORM" 2>/dev/null)
    
    echo "   Response: $LOGIN_RESPONSE2" | python3 -m json.tool 2>/dev/null || echo "   $LOGIN_RESPONSE2"
    
    TOKEN=$(echo "$LOGIN_RESPONSE2" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)
    
    if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
        echo -e "   ${GREEN}✓ Login successful with form data!${NC}"
    else
        echo -e "   ${RED}✗ Both login methods failed${NC}"
        exit 1
    fi
fi

# Test 3: Test authenticated endpoint
echo ""
echo "3. Testing authenticated endpoint (/auth/me)..."
ME_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_BASE/auth/me" \
  -H "Authorization: Bearer $TOKEN" 2>/dev/null)

HTTP_CODE=$(echo "$ME_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$ME_RESPONSE" | grep -v "HTTP_CODE:")

echo "   HTTP Status: $HTTP_CODE"
echo "   Response body:"
echo "   $BODY" | python3 -m json.tool 2>/dev/null || echo "   $BODY"

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "   ${GREEN}✓ Authentication working correctly${NC}"
else
    echo -e "   ${YELLOW}⚠ Authentication may have issues (HTTP $HTTP_CODE)${NC}"
fi

# Test 4: Test dashboard endpoint
echo ""
echo "4. Testing dashboard endpoint..."
DASHBOARD_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_BASE/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN" 2>/dev/null)

HTTP_CODE=$(echo "$DASHBOARD_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$DASHBOARD_RESPONSE" | grep -v "HTTP_CODE:")

echo "   HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "   ${GREEN}✓ Dashboard endpoint accessible${NC}"
else
    echo -e "   ${YELLOW}⚠ Dashboard endpoint returned HTTP $HTTP_CODE${NC}"
    echo "   Response: $BODY"
fi

# Test 5: Check WebSocket endpoint
echo ""
echo "5. Testing WebSocket endpoint..."
WS_URL="wss://luckygas-backend-production-154687573210.asia-east1.run.app/api/v1/websocket/ws"
echo "   WebSocket URL: $WS_URL"
echo "   Note: Full WebSocket test requires browser environment"

# Test 6: Check deployed frontend files
echo ""
echo "6. Checking frontend deployment..."
FRONTEND_URL="https://vast-tributary-466619-m8.web.app"

echo -n "   Testing frontend index.html... "
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" 2>/dev/null)
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ Frontend is deployed (HTTP $FRONTEND_RESPONSE)${NC}"
else
    echo -e "${RED}✗ Frontend not accessible (HTTP $FRONTEND_RESPONSE)${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo "Diagnostic Summary"
echo "=========================================="

if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    echo -e "${GREEN}✓ Backend API is functional${NC}"
    echo -e "${GREEN}✓ Authentication is working${NC}"
    echo ""
    echo "Token for testing:"
    echo "$TOKEN"
    echo ""
    echo "You can use this token to test API calls:"
    echo "curl -H \"Authorization: Bearer $TOKEN\" $API_BASE/[endpoint]"
else
    echo -e "${RED}✗ Critical issues detected with authentication${NC}"
fi

echo ""
echo "Next steps:"
echo "1. Check browser console for frontend errors"
echo "2. Review network tab for failed requests"
echo "3. Verify all environment variables are set correctly"
echo "4. Test with the minimal version if issues persist"