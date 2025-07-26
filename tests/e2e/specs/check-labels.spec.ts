import { test, expect } from '@playwright/test';

test('check form labels', async ({ page }) => {
  await page.goto('http://localhost:5174/login');
  
  // Wait for the login form
  await page.waitForSelector('[data-testid="username-input"]');
  
  // Get all labels
  const labels = await page.locator('label').all();
  console.log('Found', labels.length, 'labels');
  
  for (const label of labels) {
    const text = await label.textContent();
    const forAttr = await label.getAttribute('for');
    console.log(`Label: "${text}", for="${forAttr}"`);
  }
  
  // Also check the actual form structure
  const form = await page.locator('form').first();
  const formHTML = await form.innerHTML();
  console.log('Form structure:', formHTML.substring(0, 500));
});