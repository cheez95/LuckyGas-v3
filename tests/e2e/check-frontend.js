const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  console.log('Navigating to http://localhost:5174/login...');
  await page.goto('http://localhost:5174/login');
  
  console.log('Page title:', await page.title());
  console.log('Page URL:', page.url());
  
  // Wait a bit to see what's on the page
  await page.waitForTimeout(2000);
  
  // Take a screenshot
  await page.screenshot({ path: 'frontend-check.png' });
  console.log('Screenshot saved as frontend-check.png');
  
  // Get page content
  const content = await page.content();
  console.log('Page content length:', content.length);
  console.log('First 500 chars:', content.substring(0, 500));
  
  // Check for any error messages
  const bodyText = await page.locator('body').textContent();
  console.log('Body text:', bodyText?.substring(0, 500));
  
  await browser.close();
})();