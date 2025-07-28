#!/bin/bash
# Comprehensive test infrastructure validation script

set -e

echo "🔍 Lucky Gas Test Infrastructure Validation"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Results tracking
PASSED=0
FAILED=0
WARNINGS=0

# Function to check and report
check() {
  local description=$1
  local command=$2
  local expected=$3
  
  echo -n "Checking $description... "
  
  if eval "$command"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
    return 0
  else
    echo -e "${RED}✗ FAILED${NC}"
    echo "  Command: $command"
    [ -n "$expected" ] && echo "  Expected: $expected"
    ((FAILED++))
    return 1
  fi
}

warn() {
  local description=$1
  echo -e "${YELLOW}⚠ WARNING: $description${NC}"
  ((WARNINGS++))
}

section() {
  echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Start validation
section "1. Environment Setup"

check "Node.js installed" "which node > /dev/null 2>&1"
check "npm installed" "which npm > /dev/null 2>&1"
check "Python environment" "which python3 > /dev/null 2>&1"
check "uv installed" "which uv > /dev/null 2>&1"

section "2. Project Structure"

check "Backend directory exists" "[ -d backend ]"
check "Frontend directory exists" "[ -d frontend ]"
check "Tests directory exists" "[ -d tests ]"
check "E2E tests directory exists" "[ -d tests/e2e ]"

section "3. Frontend Configuration"

cd frontend
check "Frontend package.json exists" "[ -f package.json ]"
check "Frontend dependencies installed" "[ -d node_modules ]"
check "Vite config exists" "[ -f vite.config.ts ]"
check "TypeScript config exists" "[ -f tsconfig.json ]"
check "Test scripts in package.json" "grep -q '\"test\"' package.json"

# Check vite config port
echo -n "Checking Vite proxy configuration... "
if grep -q "target: 'http://localhost:8000'" vite.config.ts; then
  echo -e "${GREEN}✓ PASSED${NC}"
  ((PASSED++))
else
  echo -e "${RED}✗ FAILED${NC}"
  echo "  Vite proxy not pointing to correct backend port"
  ((FAILED++))
fi

section "4. Backend Configuration"

cd ../backend
check "Backend requirements.txt exists" "[ -f requirements.txt ]"
check "Backend .venv exists" "[ -d .venv ]"
check "Main app file exists" "[ -f app/main.py ]"

section "5. Test Infrastructure"

cd ../tests/e2e
check "Playwright config exists" "[ -f ../../playwright.config.ts ]"
check "Start services script exists" "[ -f start-services.sh ]"
check "Start services script is executable" "[ -x start-services.sh ]"
check "Stop services script exists" "[ -f stop-services.sh ]"
check "Auth test exists" "[ -f auth.spec.ts ]"
check "Page objects exist" "[ -d pages ]"

section "6. Port Availability"

check "Backend port 8000 available" "! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1"
check "Frontend port 5173 available" "! lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1"

section "7. Frontend Validation"

cd ../../frontend
echo -n "Running frontend validation script... "
if node scripts/validate-frontend.js > /dev/null 2>&1; then
  echo -e "${GREEN}✓ PASSED${NC}"
  ((PASSED++))
else
  echo -e "${RED}✗ FAILED${NC}"
  echo "  Run 'node frontend/scripts/validate-frontend.js' for details"
  ((FAILED++))
fi

section "8. Test Execution Dry Run"

cd ../tests/e2e

# Try to start services
echo -n "Testing service startup... "
if timeout 30s ./start-services.sh > /dev/null 2>&1; then
  echo -e "${GREEN}✓ PASSED${NC}"
  ((PASSED++))
  
  # Check if services are responding
  echo -n "Testing backend health endpoint... "
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/health" | grep -q "200"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
  else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
  fi
  
  echo -n "Testing frontend response... "
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:5173" | grep -q "200"; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
  else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
  fi
  
  # Stop services
  ./stop-services.sh > /dev/null 2>&1
else
  echo -e "${RED}✗ FAILED${NC}"
  echo "  Services failed to start"
  ((FAILED++))
fi

section "9. Common Issues Check"

# Check for common configuration issues
if [ -f ../../frontend/.env ]; then
  if grep -q "VITE_API_URL" ../../frontend/.env; then
    warn "VITE_API_URL in .env file may override vite.config.ts proxy"
  fi
fi

if ! grep -q "localhost" ../../backend/app/core/config.py 2>/dev/null; then
  warn "Backend may not be configured for localhost development"
fi

# Summary
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC} $FAILED"

if [ $FAILED -eq 0 ]; then
  echo -e "\n${GREEN}✅ Test infrastructure validation PASSED!${NC}"
  echo "You can now run E2E tests with confidence."
  exit 0
else
  echo -e "\n${RED}❌ Test infrastructure validation FAILED!${NC}"
  echo "Please fix the issues above before running tests."
  
  # Provide helpful next steps
  echo -e "\n${YELLOW}Suggested fixes:${NC}"
  echo "1. Ensure all dependencies are installed:"
  echo "   - cd frontend && npm install"
  echo "   - cd backend && uv pip install -r requirements.txt"
  echo "2. Fix port configuration in frontend/vite.config.ts"
  echo "3. Make scripts executable: chmod +x tests/e2e/*.sh"
  echo "4. Check for processes using ports 8000 and 5173"
  
  exit 1
fi