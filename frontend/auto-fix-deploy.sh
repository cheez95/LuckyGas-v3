#!/bin/bash

# Auto-fix and deploy script for Lucky Gas Frontend
# This script will iteratively fix map errors and deploy until successful

echo "=============================================="
echo "Lucky Gas Frontend Auto-Fix & Deploy Script"
echo "=============================================="

MAX_ATTEMPTS=3
ATTEMPT=1
FRONTEND_URL="https://vast-tributary-466619-m8.web.app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
  echo ""
  echo -e "${YELLOW}========== Attempt $ATTEMPT of $MAX_ATTEMPTS ==========${NC}"
  
  # Step 1: Build the project
  echo ""
  echo -e "${YELLOW}Step 1: Building project...${NC}"
  npm run build 2>&1 | tee build_attempt_${ATTEMPT}.log
  
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo -e "${GREEN}✅ Build successful!${NC}"
  else
    echo -e "${RED}❌ Build failed. Check build_attempt_${ATTEMPT}.log for details.${NC}"
    echo "Attempting to fix import issues..."
    
    # Try to fix common import issues
    find src -name "*.tsx" -o -name "*.jsx" | while read file; do
      # Fix relative import paths for dataHelpers
      if grep -q "dataHelpers" "$file"; then
        DIR=$(dirname "$file")
        RELATIVE_PATH=$(realpath --relative-to="$DIR" src/utils/dataHelpers.ts | sed 's/\.ts$//')
        sed -i "s|from '[^']*dataHelpers'|from './${RELATIVE_PATH}'|g" "$file"
      fi
    done
    
    ATTEMPT=$((ATTEMPT + 1))
    continue
  fi
  
  # Step 2: Deploy to Firebase
  echo ""
  echo -e "${YELLOW}Step 2: Deploying to Firebase...${NC}"
  firebase deploy --only hosting 2>&1 | tee deploy_attempt_${ATTEMPT}.log
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
  else
    echo -e "${RED}❌ Deployment failed. Check deploy_attempt_${ATTEMPT}.log${NC}"
    ATTEMPT=$((ATTEMPT + 1))
    continue
  fi
  
  # Step 3: Wait for deployment to propagate
  echo ""
  echo -e "${YELLOW}Step 3: Waiting for deployment to propagate...${NC}"
  sleep 10
  
  # Step 4: Test deployment
  echo ""
  echo -e "${YELLOW}Step 4: Testing deployment...${NC}"
  
  # Check if site is accessible
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
  
  if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Site is accessible (HTTP $HTTP_CODE)${NC}"
  else
    echo -e "${RED}❌ Site returned HTTP $HTTP_CODE${NC}"
    ATTEMPT=$((ATTEMPT + 1))
    continue
  fi
  
  # Step 5: Check for JavaScript errors
  echo ""
  echo -e "${YELLOW}Step 5: Checking for JavaScript errors...${NC}"
  
  # Create a test script to check for errors
  cat > test_frontend.js << 'EOF'
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  let jsErrors = [];
  
  // Listen for console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      jsErrors.push(msg.text());
    }
  });
  
  // Listen for page errors
  page.on('pageerror', error => {
    jsErrors.push(error.message);
  });
  
  try {
    // Navigate to the app
    await page.goto('https://vast-tributary-466619-m8.web.app', {
      waitUntil: 'networkidle2',
      timeout: 30000
    });
    
    // Wait a bit for any async errors
    await page.waitForTimeout(5000);
    
    // Check if any map errors occurred
    const mapErrors = jsErrors.filter(err => 
      err.includes('map is not a function') || 
      err.includes('Cannot read properties')
    );
    
    if (mapErrors.length > 0) {
      console.error('❌ Map errors found:');
      mapErrors.forEach(err => console.error('  -', err));
      process.exit(1);
    } else if (jsErrors.length > 0) {
      console.warn('⚠️  Other JavaScript errors found:');
      jsErrors.forEach(err => console.warn('  -', err));
      process.exit(0);
    } else {
      console.log('✅ No JavaScript errors detected!');
      process.exit(0);
    }
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
EOF
  
  # Check if puppeteer is installed
  if ! npm list puppeteer >/dev/null 2>&1; then
    echo "Installing puppeteer for testing..."
    npm install --no-save puppeteer
  fi
  
  # Run the test
  node test_frontend.js
  TEST_RESULT=$?
  
  if [ $TEST_RESULT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=============================================="
    echo "🎉 SUCCESS! Deployment completed successfully!"
    echo "=============================================="
    echo ""
    echo "Frontend URL: $FRONTEND_URL"
    echo "Test page: ${FRONTEND_URL}/#/test-data"
    echo ""
    echo "You can now:"
    echo "1. Visit the site and check the Route Planning page"
    echo "2. Open browser console to see debug logs"
    echo "3. Visit /test-data to run API tests"
    echo "=============================================="
    echo -e "${NC}"
    
    # Clean up
    rm -f test_frontend.js
    exit 0
  else
    echo -e "${RED}❌ JavaScript errors still present${NC}"
    
    # Try to get more details about the error
    echo ""
    echo "Attempting to get more error details..."
    curl -s "$FRONTEND_URL" | grep -o "TypeError.*map is not a function" | head -5
  fi
  
  ATTEMPT=$((ATTEMPT + 1))
  echo ""
  echo -e "${YELLOW}Retrying...${NC}"
done

echo ""
echo -e "${RED}=============================================="
echo "❌ Failed after $MAX_ATTEMPTS attempts"
echo "=============================================="
echo ""
echo "Please check the following:"
echo "1. Review build logs: build_attempt_*.log"
echo "2. Review deploy logs: deploy_attempt_*.log"
echo "3. Check browser console at: $FRONTEND_URL"
echo "4. Visit test page: ${FRONTEND_URL}/#/test-data"
echo ""
echo "Common issues:"
echo "- Import path errors: Check relative paths to dataHelpers"
echo "- API response format: Use test page to check actual response structure"
echo "- Missing null checks: Add toArray() or safeMap() calls"
echo "=============================================="
echo -e "${NC}"

# Clean up
rm -f test_frontend.js
exit 1