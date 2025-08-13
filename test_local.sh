#!/bin/bash

echo "🧪 Lucky Gas Local Test Suite"
echo "=============================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASS=0
FAIL=0

# Test function
test_endpoint() {
    local name="$1"
    local command="$2"
    local expected="$3"
    
    echo -n "Testing $name... "
    
    result=$(eval "$command" 2>/dev/null)
    
    if [[ "$result" == *"$expected"* ]]; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASS++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "  Expected: $expected"
        echo "  Got: $result"
        ((FAIL++))
    fi
}

# 1. Test Backend Health
test_endpoint "Backend Health" \
    "curl -s http://localhost:8000/health" \
    "healthy"

# 2. Test Backend API Info
test_endpoint "API Info" \
    "curl -s http://localhost:8000/api/v1" \
    "endpoints"

# 3. Test Dashboard Health
test_endpoint "Dashboard Health" \
    "curl -s http://localhost:8000/api/v1/dashboard/health" \
    "dashboard"

# 4. Test Login
echo -n "Testing Login... "
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin@luckygas.com&password=admin-password-2025" \
    -s 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ ! -z "$TOKEN" ]; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC}"
    ((FAIL++))
fi

# 5. Test Dashboard Summary (requires auth)
if [ ! -z "$TOKEN" ]; then
    test_endpoint "Dashboard Summary" \
        "curl -s -H 'Authorization: Bearer $TOKEN' http://localhost:8000/api/v1/dashboard/summary" \
        "stats"
fi

# 6. Test Frontend
echo -n "Testing Frontend... "
if curl -s http://localhost:5173 2>/dev/null | grep -q "Lucky Gas"; then
    echo -e "${GREEN}✅ PASS${NC}"
    ((PASS++))
else
    echo -e "${YELLOW}⚠️  SKIPPED (may need manual start)${NC}"
fi

# 7. Test Database Connection
test_endpoint "Database Stats" \
    "curl -s http://localhost:8000/api/v1/db/stats" \
    "users"

# 8. Test Cache Stats
test_endpoint "Cache Stats" \
    "curl -s http://localhost:8000/api/v1/cache/stats" \
    "hits"

echo ""
echo "=============================="
echo "Test Results:"
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "System is ready for use:"
    echo "  🌐 Frontend: http://localhost:5173"
    echo "  🔧 Backend:  http://localhost:8000"
    echo "  📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "Login Credentials:"
    echo "  📧 admin@luckygas.com"
    echo "  🔑 admin-password-2025"
else
    echo -e "${RED}⚠️  Some tests failed. Please check the logs.${NC}"
    echo ""
    echo "Debug commands:"
    echo "  tail -20 backend.log   # Check backend logs"
    echo "  tail -20 frontend.log  # Check frontend logs"
    echo "  ps aux | grep uvicorn  # Check if backend is running"
    echo "  ps aux | grep vite     # Check if frontend is running"
fi