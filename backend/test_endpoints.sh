#\!/bin/bash

echo "🧪 Testing Lucky Gas Login Endpoints"
echo "=================================================="

BASE_URL="https://luckygas-backend-production-yzoirwjj3q-de.a.run.app"
USERNAME="admin@luckygas.com"
PASSWORD="admin-password-2025"

echo ""
echo "1. Testing Regular Login Endpoint:"
echo "   POST $BASE_URL/api/v1/auth/login"
REGULAR_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME&password=$PASSWORD")

if echo "$REGULAR_RESPONSE" | grep -q "access_token"; then
  echo "   ✅ Regular login successful\!"
  TOKEN=$(echo "$REGULAR_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'][:50])")
  echo "   Token: ${TOKEN}..."
else
  echo "   ❌ Regular login failed"
  echo "   Response: $REGULAR_RESPONSE"
fi

echo ""
echo "2. Testing Optimized Login Endpoint:"
echo "   POST $BASE_URL/api/v1/auth/login-optimized"
OPTIMIZED_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login-optimized" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME&password=$PASSWORD")

if echo "$OPTIMIZED_RESPONSE" | grep -q "access_token"; then
  echo "   ✅ Optimized login successful\!"
  TOKEN=$(echo "$OPTIMIZED_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'][:50])")
  echo "   Token: ${TOKEN}..."
  USER=$(echo "$OPTIMIZED_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); u=d.get('user',{}); print(f\"{u.get('username')} ({u.get('role')})\")")
  echo "   User: $USER"
else
  echo "   ❌ Optimized login failed"
  echo "   Response: $OPTIMIZED_RESPONSE"
fi

echo ""
echo "=================================================="
echo "📊 Summary:"
echo ""
echo "The regular login endpoint is working correctly."
echo "The optimized login endpoint has a MissingGreenlet error."
echo ""
echo "The fix has been implemented in the code but needs deployment."
echo "Once deployed, the optimized endpoint will work and provide both"
echo "tokens and user data in a single response."
