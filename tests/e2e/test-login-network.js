const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Capture console messages
  page.on('console', msg => {
    console.log('BROWSER CONSOLE:', msg.type(), '-', msg.text());
  });
  
  // Capture network failures
  page.on('requestfailed', request => {
    console.log('REQUEST FAILED:', request.url(), '-', request.failure()?.errorText);
  });
  
  // Capture responses
  page.on('response', response => {
    if (response.url().includes('/api/')) {
      console.log('API RESPONSE:', response.url(), '-', response.status());
    }
  });
  
  try {
    console.log('1. Navigating to login page...');
    await page.goto('http://localhost:5173/login');
    
    console.log('2. Waiting for login form...');
    await page.waitForSelector('input[data-testid="username-input"]', { timeout: 10000 });
    
    console.log('3. Filling login form...');
    await page.fill('input[data-testid="username-input"]', 'driver@luckygas.com.tw');
    await page.fill('input[data-testid="password-input"]', 'Driver123!');
    
    console.log('4. Clicking login button...');
    await page.click('button[data-testid="login-button"]');
    
    console.log('5. Waiting for result...');
    await page.waitForTimeout(3000); // Wait to see what happens
    
    console.log('6. Current URL:', page.url());
    
    // Check localStorage for token
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    console.log('7. Auth token exists:', !!token);
    
    // Check for error message
    const errorMessage = await page.locator('[role="alert"]').textContent().catch(() => null);
    if (errorMessage) {
      console.log('8. Error message:', errorMessage);
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  }
  
  await page.waitForTimeout(5000); // Keep browser open
  await browser.close();
})();