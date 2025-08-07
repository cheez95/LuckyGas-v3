import { Page } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

export async function loginAsManager(page: Page) {
  await page.goto(BASE_URL);
  await page.fill('input[placeholder*="用戶名"]', 'manager@luckygas.com');
  await page.fill('input[placeholder*="密碼"]', 'manager123');
  await page.click('button:has-text("登 入")');
  await page.waitForURL(/dashboard/);
}

export async function loginAsDriver(page: Page) {
  await page.goto(BASE_URL);
  await page.fill('input[placeholder*="用戶名"]', 'driver@luckygas.com');
  await page.fill('input[placeholder*="密碼"]', 'driver123');
  await page.click('button:has-text("登 入")');
  await page.waitForURL(/dashboard/);
}

export async function loginAsCustomer(page: Page) {
  await page.goto(BASE_URL);
  await page.fill('input[placeholder*="用戶名"]', 'customer@luckygas.com');
  await page.fill('input[placeholder*="密碼"]', 'customer123');
  await page.click('button:has-text("登 入")');
  await page.waitForURL(/dashboard/);
}

export async function loginAsOfficeStaff(page: Page) {
  await page.goto(BASE_URL);
  await page.fill('input[placeholder*="用戶名"]', 'staff@luckygas.com');
  await page.fill('input[placeholder*="密碼"]', 'staff123');
  await page.click('button:has-text("登 入")');
  await page.waitForURL(/dashboard/);
}

// Default test user that we know exists
export async function loginAsTestUser(page: Page) {
  await page.goto(BASE_URL);
  await page.fill('input[placeholder*="用戶名"]', 'test@example.com');
  await page.fill('input[placeholder*="密碼"]', 'test123');
  await page.click('button:has-text("登 入")');
  await page.waitForURL(/dashboard/);
}

export async function getAuthToken(): Promise<string> {
  // This would normally make an API call to get a token
  // For now, return a mock token
  return 'mock-auth-token';
}

export async function logout(page: Page) {
  await page.click('text=Test User');
  await page.click('text=登出');
  await page.waitForURL(/login/);
}

export async function waitForApiResponse(page: Page, endpoint: string) {
  return page.waitForResponse(response => 
    response.url().includes(endpoint) && response.status() === 200
  );
}