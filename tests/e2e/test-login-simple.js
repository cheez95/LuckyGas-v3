const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
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
    
    console.log('5. Waiting for navigation...');
    await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 10000 });
    
    console.log('6. Success! Current URL:', page.url());
    
    // Check localStorage for token
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    console.log('7. Auth token exists:', !!token);
    
  } catch (error) {
    console.error('Error:', error.message);
    console.log('Current URL:', page.url());
    
    // Take screenshot for debugging
    await page.screenshot({ path: 'login-debug.png' });
    console.log('Screenshot saved as login-debug.png');
  }
  
  await browser.close();
})();