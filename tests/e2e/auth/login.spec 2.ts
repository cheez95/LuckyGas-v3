import { test, expect } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const API_URL = process.env.API_URL || 'http://localhost:8000';

// Test data
const TEST_USERS = {
  admin: {
    username: 'admin@luckygas.com',
    password: 'admin-password-2025',
    expectedRole: 'SUPER_ADMIN'
  },
  invalid: {
    username: 'invalid@example.com',
    password: 'wrongpassword'
  }
};

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing auth data
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('Successful admin login', async ({ page }) => {
    // Navigate to login page
    await page.goto(`${BASE_URL}/login`);
    
    // Check page loaded correctly
    await expect(page).toHaveTitle(/幸福氣配送管理系統/);
    
    // Fill login form
    await page.fill('[data-testid="username-input"]', TEST_USERS.admin.username);
    await page.fill('[data-testid="password-input"]', TEST_USERS.admin.password);
    
    // Click login button
    await page.click('[data-testid="login-button"]');
    
    // Wait for navigation
    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 10000
    });
    
    // Verify we're logged in
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
    
    // Check user info in localStorage
    const userInfo = await page.evaluate(() => {
      const stored = localStorage.getItem('user');
      return stored ? JSON.parse(stored) : null;
    });
    expect(userInfo).toBeTruthy();
    expect(userInfo.email).toBe(TEST_USERS.admin.username);
    expect(userInfo.role).toBe(TEST_USERS.admin.expectedRole);
  });

  test('Invalid credentials show error', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Fill with invalid credentials
    await page.fill('[data-testid="username-input"]', TEST_USERS.invalid.username);
    await page.fill('[data-testid="password-input"]', TEST_USERS.invalid.password);
    
    // Click login
    await page.click('[data-testid="login-button"]');
    
    // Check for error message
    await expect(page.locator('.ant-alert-error')).toBeVisible({ timeout: 5000 });
    
    // Verify we're still on login page
    await expect(page).toHaveURL(/.*\/login/);
    
    // Verify no token was stored
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeNull();
  });

  test('Empty form validation', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Click login without filling form
    await page.click('[data-testid="login-button"]');
    
    // Check for validation messages
    await expect(page.locator('text=請輸入用戶名')).toBeVisible();
    await expect(page.locator('text=請輸入密碼')).toBeVisible();
  });

  test('Password visibility toggle', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    const passwordInput = page.locator('[data-testid="password-input"]');
    
    // Initially password should be hidden
    await expect(passwordInput).toHaveAttribute('type', 'password');
    
    // Click eye icon
    await page.click('[data-testid="password-toggle"]');
    
    // Password should be visible
    await expect(passwordInput).toHaveAttribute('type', 'text');
    
    // Click again to hide
    await page.click('[data-testid="password-toggle"]');
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('Session persistence across page reload', async ({ page }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);
    await page.fill('[data-testid="username-input"]', TEST_USERS.admin.username);
    await page.fill('[data-testid="password-input"]', TEST_USERS.admin.password);
    await page.click('[data-testid="login-button"]');
    
    // Wait for successful login
    await page.waitForURL((url) => !url.pathname.includes('/login'));
    
    // Reload page
    await page.reload();
    
    // Should still be logged in
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeTruthy();
    
    // Should not redirect to login
    await expect(page).not.toHaveURL(/.*\/login/);
  });

  test('Logout functionality', async ({ page }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);
    await page.fill('[data-testid="username-input"]', TEST_USERS.admin.username);
    await page.fill('[data-testid="password-input"]', TEST_USERS.admin.password);
    await page.click('[data-testid="login-button"]');
    
    // Wait for dashboard
    await page.waitForURL((url) => !url.pathname.includes('/login'));
    
    // Click user dropdown
    await page.click('[data-testid="user-dropdown"]');
    
    // Click logout
    await page.click('[data-testid="logout-button"]');
    
    // Should redirect to login
    await page.waitForURL(/.*\/login/);
    
    // Token should be cleared
    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeNull();
  });
});

test.describe('Authentication API Tests', () => {
  test('API health check', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/v1/health`);
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body.status).toBe('healthy');
    expect(body.service).toBe('minimal-backend');
  });

  test('Login API returns valid token', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/v1/auth/login`, {
      form: {
        username: TEST_USERS.admin.username,
        password: TEST_USERS.admin.password
      }
    });
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body.access_token).toBeTruthy();
    expect(body.token_type).toBe('bearer');
    expect(body.user).toBeTruthy();
    expect(body.user.email).toBe(TEST_USERS.admin.username);
  });

  test('Invalid login returns 401', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/v1/auth/login`, {
      form: {
        username: TEST_USERS.invalid.username,
        password: TEST_USERS.invalid.password
      }
    });
    
    expect(response.status()).toBe(401);
    
    const body = await response.json();
    expect(body.detail).toContain('使用者名稱或密碼錯誤');
  });
});