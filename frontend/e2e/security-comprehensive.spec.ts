import { test, expect, Page } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';

// Security test payloads
const XSS_PAYLOADS = [
  '<script>alert("XSS")</script>',
  '<img src=x onerror=alert("XSS")>',
  'javascript:alert("XSS")',
  '<svg onload=alert("XSS")>',
  '"><script>alert("XSS")</script>',
  '<iframe src="javascript:alert(\'XSS\')"></iframe>',
  '<body onload=alert("XSS")>',
  '${alert("XSS")}',
  '{{constructor.constructor("alert(1)")()}}'
];

const SQL_INJECTION_PAYLOADS = [
  "' OR '1'='1",
  "1' OR '1' = '1",
  "' OR 1=1--",
  "admin'--",
  "1' UNION SELECT NULL--",
  "' OR 'a'='a"
];

const CSRF_TEST_ORIGIN = 'http://evil.com';

// Helper to check for XSS vulnerability
async function checkXSS(page: Page, selector: string, payload: string): Promise<boolean> {
  let alertTriggered = false;
  
  page.on('dialog', async dialog => {
    alertTriggered = true;
    await dialog.dismiss();
  });

  await page.fill(selector, payload);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(1000);

  // Check if payload is properly escaped in DOM
  const content = await page.content();
  const isEscaped = !content.includes(payload) || content.includes(payload.replace(/</g, '&lt;'));

  return !alertTriggered && isEscaped;
}

test.describe('Comprehensive Security Testing', () => {
  test.describe('Authentication Security', () => {
    test('Password security requirements', async ({ page }) => {
      await page.goto('/forgot-password');
      
      // Test weak passwords
      const weakPasswords = ['123456', 'password', 'admin123', 'aaaaaaa'];
      
      for (const password of weakPasswords) {
        await page.fill('[data-testid="new-password-input"]', password);
        await page.fill('[data-testid="confirm-password-input"]', password);
        await page.click('[data-testid="reset-password-btn"]');
        
        // Should show password strength error
        await expect(page.locator('[data-testid="password-strength-error"]')).toBeVisible();
      }

      // Test strong password
      const strongPassword = 'SecureP@ssw0rd123!';
      await page.fill('[data-testid="new-password-input"]', strongPassword);
      await page.fill('[data-testid="confirm-password-input"]', strongPassword);
      
      // Should accept strong password
      await expect(page.locator('[data-testid="password-strength-good"]')).toBeVisible();
    });

    test('Brute force protection', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();

      // Attempt multiple failed logins
      for (let i = 0; i < 6; i++) {
        await loginPage.login('admin', 'wrongpassword');
        await page.waitForTimeout(500);
      }

      // Should show rate limiting or account lockout
      await expect(page.locator('[data-testid="rate-limit-error"]')).toBeVisible();
      
      // Check if temporarily blocked
      await loginPage.login('admin', 'correctpassword');
      await expect(page.locator('[data-testid="account-locked"]')).toBeVisible();
    });

    test('Session security', async ({ page, context }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      // Get session cookie
      const cookies = await context.cookies();
      const sessionCookie = cookies.find(c => c.name.includes('session') || c.name.includes('token'));

      // Check secure cookie attributes
      expect(sessionCookie).toBeDefined();
      expect(sessionCookie?.secure).toBeTruthy(); // HTTPS only
      expect(sessionCookie?.httpOnly).toBeTruthy(); // No JS access
      expect(sessionCookie?.sameSite).toBe('Strict'); // CSRF protection

      // Test session timeout
      // Manipulate cookie expiry
      if (sessionCookie) {
        await context.addCookies([{
          ...sessionCookie,
          expires: Date.now() / 1000 - 3600 // Expired 1 hour ago
        }]);
      }

      await page.reload();
      await expect(page).toHaveURL(/login/);
    });

    test('JWT token security', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      // Intercept API calls to check JWT
      let jwtToken = '';
      page.on('request', request => {
        const authHeader = request.headers()['authorization'];
        if (authHeader && authHeader.startsWith('Bearer ')) {
          jwtToken = authHeader.replace('Bearer ', '');
        }
      });

      // Make an API call
      await page.goto('/orders');
      await page.waitForLoadState('networkidle');

      // Validate JWT structure
      expect(jwtToken).toBeTruthy();
      const jwtParts = jwtToken.split('.');
      expect(jwtParts).toHaveLength(3); // Header.Payload.Signature

      // Decode and check payload (without verification)
      const payload = JSON.parse(atob(jwtParts[1]));
      expect(payload.exp).toBeDefined(); // Has expiration
      expect(payload.iat).toBeDefined(); // Has issued at
      expect(payload.sub).toBeDefined(); // Has subject
    });
  });

  test.describe('XSS Prevention', () => {
    test.beforeEach(async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');
    });

    test('Input field XSS protection', async ({ page }) => {
      await page.goto('/customers');
      await page.click('[data-testid="create-customer-btn"]');

      const inputFields = [
        '[data-testid="customer-name-input"]',
        '[data-testid="customer-address-input"]',
        '[data-testid="customer-notes-input"]'
      ];

      for (const field of inputFields) {
        for (const payload of XSS_PAYLOADS.slice(0, 3)) {
          const isSecure = await checkXSS(page, field, payload);
          expect(isSecure).toBeTruthy();
        }
      }
    });

    test('Search functionality XSS protection', async ({ page }) => {
      await page.goto('/orders');

      for (const payload of XSS_PAYLOADS.slice(0, 3)) {
        await page.fill('[data-testid="search-input"]', payload);
        await page.keyboard.press('Enter');
        await page.waitForTimeout(500);

        // Check search results don't execute script
        const content = await page.content();
        expect(content).not.toContain('<script>');
        expect(content).not.toContain('javascript:');
        
        // Check reflected in search box is escaped
        const searchValue = await page.inputValue('[data-testid="search-input"]');
        expect(searchValue).toBe(payload); // Original value preserved
      }
    });

    test('URL parameter XSS protection', async ({ page }) => {
      // Test various URL injection attempts
      const xssUrls = [
        '/orders?search=<script>alert("XSS")</script>',
        '/customers?filter="><img src=x onerror=alert("XSS")>',
        '/dashboard#<script>alert("XSS")</script>'
      ];

      for (const url of xssUrls) {
        let alertTriggered = false;
        page.on('dialog', dialog => {
          alertTriggered = true;
          dialog.dismiss();
        });

        await page.goto(url);
        await page.waitForTimeout(1000);

        expect(alertTriggered).toBeFalsy();
      }
    });

    test('Rich text editor XSS protection', async ({ page }) => {
      await page.goto('/orders');
      await page.click('[data-testid="create-order-btn"]');

      const richTextEditor = page.locator('[data-testid="delivery-notes-editor"]');
      if (await richTextEditor.isVisible()) {
        // Test HTML injection
        await richTextEditor.fill('<h1>Test</h1><script>alert("XSS")</script>');
        
        // Save and reload
        await page.click('[data-testid="save-order-btn"]');
        await page.waitForTimeout(1000);

        // Check rendered content
        const renderedContent = await page.locator('[data-testid="delivery-notes-display"]').innerHTML();
        expect(renderedContent).not.toContain('<script>');
        expect(renderedContent).toContain('&lt;script&gt;'); // Should be escaped
      }
    });
  });

  test.describe('CSRF Protection', () => {
    test('CSRF token validation', async ({ browser }) => {
      const context = await browser.newContext();
      const page = await context.newPage();

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      // Get CSRF token
      const csrfToken = await page.evaluate(() => {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
               (window as any).csrfToken ||
               document.cookie.match(/csrf_token=([^;]+)/)?.[1];
      });

      expect(csrfToken).toBeTruthy();

      // Test POST request without CSRF token
      const response = await page.evaluate(async () => {
        try {
          const res = await fetch('/api/orders', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ test: 'data' })
            // Intentionally omitting CSRF token
          });
          return { status: res.status, ok: res.ok };
        } catch (error) {
          return { error: error.message };
        }
      });

      // Should be rejected without valid CSRF token
      expect(response.ok).toBeFalsy();
      expect(response.status).toBe(403); // Forbidden

      await context.close();
    });

    test('Cross-origin request blocking', async ({ browser }) => {
      const context = await browser.newContext();
      const page = await context.newPage();

      // Try to make request from different origin
      await page.goto(CSRF_TEST_ORIGIN);
      
      const response = await page.evaluate(async (apiUrl) => {
        try {
          const res = await fetch(`${apiUrl}/api/orders`, {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ malicious: 'data' })
          });
          return { status: res.status, headers: res.headers };
        } catch (error) {
          return { error: error.message };
        }
      }, process.env.VITE_API_URL || 'http://localhost:8000');

      // Should be blocked by CORS
      expect(response.error).toContain('CORS');

      await context.close();
    });
  });

  test.describe('SQL Injection Prevention', () => {
    test.beforeEach(async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');
    });

    test('Search queries SQL injection', async ({ page }) => {
      await page.goto('/customers');

      for (const payload of SQL_INJECTION_PAYLOADS) {
        await page.fill('[data-testid="search-input"]', payload);
        await page.keyboard.press('Enter');
        
        // Wait for search results
        await page.waitForTimeout(1000);

        // Should not cause error or return all records
        await expect(page.locator('[data-testid="error-message"]')).not.toBeVisible();
        
        // Check if returns reasonable results (not all records)
        const resultCount = await page.locator('.ant-table-row').count();
        expect(resultCount).toBeLessThan(10); // Assuming not returning all records
      }
    });

    test('Form inputs SQL injection', async ({ page }) => {
      await page.goto('/orders');
      await page.click('[data-testid="create-order-btn"]');

      // Try SQL injection in various fields
      await page.fill('[data-testid="customer-search"]', "'; DROP TABLE orders; --");
      await page.keyboard.press('Enter');

      // Should handle gracefully
      await expect(page.locator('[data-testid="error-500"]')).not.toBeVisible();
    });
  });

  test.describe('Authorization & Access Control', () => {
    test('Role-based access control', async ({ browser }) => {
      // Test different user roles
      const roleTests = [
        { user: 'driver1', password: 'driver123', forbiddenPaths: ['/admin', '/orders', '/customers'] },
        { user: 'customer1', password: 'customer123', forbiddenPaths: ['/admin', '/routes', '/dispatch'] },
        { user: 'office1', password: 'office123', forbiddenPaths: ['/admin/financial'] }
      ];

      for (const roleTest of roleTests) {
        const context = await browser.newContext();
        const page = await context.newPage();

        const loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login(roleTest.user, roleTest.password);

        // Try to access forbidden paths
        for (const path of roleTest.forbiddenPaths) {
          await page.goto(path);
          
          // Should either redirect or show forbidden
          const url = page.url();
          const isForbidden = url.includes('403') || url.includes('forbidden') || !url.includes(path);
          expect(isForbidden).toBeTruthy();
        }

        await context.close();
      }
    });

    test('API endpoint authorization', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      // Try to access admin API endpoints
      const response = await page.evaluate(async () => {
        try {
          const res = await fetch('/api/admin/users', {
            method: 'GET',
            credentials: 'include'
          });
          return { status: res.status };
        } catch (error) {
          return { error: error.message };
        }
      });

      // Should be forbidden for non-admin
      expect(response.status).toBe(403);
    });
  });

  test.describe('Data Security', () => {
    test('Sensitive data masking', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      await page.goto('/customers');
      
      // Check phone numbers are masked
      const phoneNumbers = await page.locator('[data-testid="customer-phone"]').all();
      for (const phone of phoneNumbers) {
        const text = await phone.textContent();
        expect(text).toMatch(/\d{4}\*{4}\d{2,4}/); // Format: 0912****5678
      }

      // Check full number visible only on detail view
      await page.locator('.ant-table-row').first().click();
      await expect(page.locator('[data-testid="full-phone-number"]')).toBeVisible();
    });

    test('Secure file upload', async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      await page.goto('/orders');
      await page.click('[data-testid="import-orders-btn"]');

      // Try to upload malicious file types
      const maliciousFiles = [
        { name: 'exploit.exe', type: 'application/exe' },
        { name: 'script.js', type: 'text/javascript' },
        { name: 'hack.php', type: 'application/php' }
      ];

      for (const file of maliciousFiles) {
        const fileChooserPromise = page.waitForEvent('filechooser');
        await page.click('[data-testid="file-upload-btn"]');
        const fileChooser = await fileChooserPromise;

        // Create fake file
        await fileChooser.setFiles({
          name: file.name,
          mimeType: file.type,
          buffer: Buffer.from('malicious content')
        });

        // Should reject dangerous file types
        await expect(page.locator('[data-testid="file-type-error"]')).toBeVisible();
      }
    });
  });

  test.describe('Network Security', () => {
    test('HTTPS enforcement', async ({ page }) => {
      // Try to access via HTTP
      const httpUrl = (process.env.VITE_APP_URL || 'https://localhost:5173').replace('https://', 'http://');
      
      const response = await page.goto(httpUrl, { waitUntil: 'domcontentloaded' });
      
      // Should redirect to HTTPS or refuse connection
      expect(page.url().startsWith('https://')).toBeTruthy();
    });

    test('Security headers', async ({ page }) => {
      const response = await page.goto('/');
      const headers = response?.headers() || {};

      // Check security headers
      expect(headers['x-frame-options']).toBe('DENY');
      expect(headers['x-content-type-options']).toBe('nosniff');
      expect(headers['x-xss-protection']).toBe('1; mode=block');
      expect(headers['strict-transport-security']).toContain('max-age=');
      expect(headers['content-security-policy']).toBeDefined();
    });
  });

  test.describe('Logging & Monitoring', () => {
    test('No sensitive data in console', async ({ page }) => {
      const consoleLogs: string[] = [];
      page.on('console', msg => {
        consoleLogs.push(msg.text());
      });

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      await page.goto('/customers');
      await page.goto('/orders');

      // Check logs don't contain sensitive data
      const sensitivePatterns = [
        /password/i,
        /token/i,
        /api[_-]?key/i,
        /secret/i,
        /\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}/, // Credit card
        /\d{3}-\d{2}-\d{4}/ // SSN
      ];

      for (const log of consoleLogs) {
        for (const pattern of sensitivePatterns) {
          expect(log).not.toMatch(pattern);
        }
      }
    });
  });
});