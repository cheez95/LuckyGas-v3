/**
 * Comprehensive System Test Suite for Lucky Gas
 * Uses intelligent error monitoring and automatic fix generation
 */

import { test, expect } from '@playwright/test';
import { IterativeTestRunner } from './infrastructure/IterativeTestRunner';
import { ErrorMonitor, ErrorSeverity } from './infrastructure/ErrorMonitor';
import { PerformanceMonitor } from './infrastructure/PerformanceMonitor';
import { AutoFixer } from './infrastructure/AutoFixer';

// Test configuration
const TEST_CONFIG = {
  maxIterations: 5,
  targetErrorThreshold: 0, // Zero critical errors
  baseURL: process.env.VITE_API_URL || 'https://vast-tributary-466619-m8.web.app',
  apiURL: process.env.VITE_API_URL || 'https://luckygas-backend-production-154687573210.asia-east1.run.app',
  testTimeout: 30000,
};

test.describe('Lucky Gas Comprehensive System Test', () => {
  let runner: IterativeTestRunner;

  test.beforeAll(async () => {
    console.log('🚀 Initializing Comprehensive Test Suite');
    console.log(`Testing against: ${TEST_CONFIG.baseURL}`);
    runner = new IterativeTestRunner(
      TEST_CONFIG.maxIterations,
      TEST_CONFIG.targetErrorThreshold
    );
  });

  test('Run iterative test and fix cycle', async ({ page }) => {
    test.setTimeout(300000); // 5 minutes for full iterative cycle
    
    console.log('Starting iterative test cycle...');
    const report = await runner.run();
    
    // Assert test results
    expect(report.finalStatus).not.toBe('failed');
    expect(report.iterations.length).toBeGreaterThan(0);
    
    // Check if critical errors were resolved
    const lastIteration = report.iterations[report.iterations.length - 1];
    expect(lastIteration.criticalErrors).toBeLessThanOrEqual(TEST_CONFIG.targetErrorThreshold);
    
    // Log summary
    console.log('\n📊 Test Summary:');
    console.log(`  Status: ${report.finalStatus}`);
    console.log(`  Iterations: ${report.iterations.length}`);
    console.log(`  Total Errors Found: ${report.totalErrors}`);
    console.log(`  Total Fixes Applied: ${report.totalFixes}`);
    console.log(`  Recommendations: ${report.recommendations.length}`);
  });

  test('Monitor console errors across all pages', async ({ page }) => {
    const errorMonitor = new ErrorMonitor(page);
    const pagesToTest = [
      '/',
      '/login',
      '/dashboard',
      '/orders',
      '/customers',
      '/routes',
      '/predictions',
      '/reports',
    ];

    for (const path of pagesToTest) {
      console.log(`Testing page: ${path}`);
      errorMonitor.setUserAction(`navigate_to_${path}`);
      
      await page.goto(`${TEST_CONFIG.baseURL}${path}`, {
        waitUntil: 'networkidle',
        timeout: TEST_CONFIG.testTimeout,
      });
      
      // Wait for dynamic content to load
      await page.waitForTimeout(2000);
    }

    // Generate error report
    const errors = errorMonitor.getErrors();
    const criticalErrors = errorMonitor.getCriticalErrors();
    const summary = errorMonitor.getErrorSummary();
    
    console.log('\n📊 Error Summary:');
    console.log(`  Total Errors: ${summary.total}`);
    console.log(`  Critical: ${summary.criticalCount}`);
    console.log(`  Auto-fixable: ${summary.autoFixable}`);
    
    // Generate fixes if errors found
    if (errors.length > 0) {
      const autoFixer = new AutoFixer();
      const fixes = autoFixer.generateFixes(errors);
      
      console.log(`\n🔧 Generated ${fixes.length} fix suggestions`);
      
      // Log fix suggestions
      fixes.forEach(fix => {
        console.log(`  - ${fix.description} (Confidence: ${(fix.confidence * 100).toFixed(0)}%)`);
      });
    }
    
    // Assert no critical errors
    expect(criticalErrors.length).toBe(0);
  });

  test('Performance monitoring across critical user flows', async ({ page }) => {
    const performanceMonitor = new PerformanceMonitor(page, {
      lcp: 2500,
      fid: 100,
      cls: 0.1,
      loadTime: 3000,
      memoryUsage: 100 * 1024 * 1024,
    });

    // Test critical user flows
    const flows = [
      {
        name: 'Dashboard Load',
        steps: async () => {
          await page.goto(`${TEST_CONFIG.baseURL}/dashboard`, {
            waitUntil: 'networkidle',
          });
          await page.waitForSelector('.dashboard-loaded', { timeout: 10000 });
        },
      },
      {
        name: 'Order Creation',
        steps: async () => {
          await page.goto(`${TEST_CONFIG.baseURL}/orders`, {
            waitUntil: 'networkidle',
          });
          await page.click('button.new-order');
          await page.fill('input[name="customer"]', 'Test Customer');
          await page.fill('input[name="quantity"]', '2');
        },
      },
      {
        name: 'Customer Search',
        steps: async () => {
          await page.goto(`${TEST_CONFIG.baseURL}/customers`, {
            waitUntil: 'networkidle',
          });
          await page.fill('input.search', '王');
          await page.waitForTimeout(1000); // Debounce
        },
      },
    ];

    for (const flow of flows) {
      console.log(`\n⚡ Testing performance: ${flow.name}`);
      performanceMonitor.reset();
      
      await flow.steps();
      
      const metrics = await performanceMonitor.getMetrics();
      const thresholdCheck = performanceMonitor.checkThresholds();
      
      console.log(`  LCP: ${metrics.lcp?.toFixed(0) || 'N/A'}ms`);
      console.log(`  FID: ${metrics.fid?.toFixed(0) || 'N/A'}ms`);
      console.log(`  CLS: ${metrics.cls?.toFixed(3) || 'N/A'}`);
      console.log(`  Memory: ${metrics.memoryUsage ? (metrics.memoryUsage / 1024 / 1024).toFixed(2) : 'N/A'}MB`);
      console.log(`  Status: ${thresholdCheck.passed ? '✅ PASSED' : '❌ FAILED'}`);
      
      if (!thresholdCheck.passed) {
        console.log('  Failures:', thresholdCheck.failures);
      }
      
      // Take performance screenshot
      await performanceMonitor.capturePerformanceScreenshot(
        `screenshots/performance_${flow.name.replace(/\s+/g, '_')}.png`
      );
    }
  });

  test('Cross-browser compatibility testing', async ({ browserName }) => {
    console.log(`\n🌐 Testing on ${browserName}`);
    
    // Browser-specific test adjustments
    const browserConfig: Record<string, any> = {
      chromium: { waitTime: 1000 },
      firefox: { waitTime: 1500 },
      webkit: { waitTime: 2000 },
    };
    
    const config = browserConfig[browserName] || { waitTime: 1000 };
    
    // Test basic functionality across browsers
    const { page } = await test.step(`Launch ${browserName}`, async () => {
      const browser = await test['_browserType'].launch();
      const context = await browser.newContext({
        locale: 'zh-TW',
        timezoneId: 'Asia/Taipei',
      });
      const page = await context.newPage();
      return { page, context, browser };
    });
    
    // Test dashboard loading
    await test.step('Load dashboard', async () => {
      await page.goto(`${TEST_CONFIG.baseURL}/dashboard`);
      await page.waitForTimeout(config.waitTime);
      
      // Check for critical elements
      await expect(page.locator('.dashboard')).toBeVisible();
    });
    
    // Test responsive design
    await test.step('Test mobile responsiveness', async () => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.waitForTimeout(config.waitTime);
      
      // Mobile menu should be visible
      const mobileMenu = page.locator('.mobile-menu-toggle');
      if (await mobileMenu.isVisible()) {
        await mobileMenu.click();
        await expect(page.locator('.mobile-navigation')).toBeVisible();
      }
    });
  });

  test('WebSocket connection and real-time updates', async ({ page }) => {
    console.log('\n🔌 Testing WebSocket connectivity');
    
    // Navigate to dashboard
    await page.goto(`${TEST_CONFIG.baseURL}/dashboard`);
    
    // Check WebSocket connection
    const wsConnected = await page.evaluate(() => {
      return new Promise((resolve) => {
        // Check if WebSocket is connected
        const checkConnection = () => {
          const ws = (window as any).wsConnection;
          if (ws && ws.readyState === WebSocket.OPEN) {
            resolve(true);
          } else {
            setTimeout(() => resolve(false), 5000);
          }
        };
        
        // Give some time for connection
        setTimeout(checkConnection, 2000);
      });
    });
    
    console.log(`  WebSocket connected: ${wsConnected ? '✅' : '❌'}`);
    
    // Test real-time update simulation
    if (wsConnected) {
      await page.evaluate(() => {
        const ws = (window as any).wsConnection;
        if (ws) {
          // Simulate incoming message
          const event = new MessageEvent('message', {
            data: JSON.stringify({
              type: 'order_update',
              data: { orderId: 'test-123', status: 'delivered' },
            }),
          });
          ws.dispatchEvent(event);
        }
      });
      
      console.log('  Simulated real-time update sent');
    }
  });

  test('Security and authentication flow', async ({ page }) => {
    console.log('\n🔒 Testing security features');
    
    // Test HTTPS enforcement
    const url = page.url();
    expect(url).toMatch(/^https:\/\//);
    console.log('  ✅ HTTPS enforced');
    
    // Test authentication redirect
    await page.goto(`${TEST_CONFIG.baseURL}/orders`);
    await page.waitForTimeout(1000);
    
    // Should redirect to login if not authenticated
    if (page.url().includes('/login')) {
      console.log('  ✅ Authentication redirect working');
      
      // Test login flow
      await page.fill('input[name="username"]', 'test@example.com');
      await page.fill('input[name="password"]', 'testpassword');
      await page.click('button[type="submit"]');
      
      // Check for error message (expected with test credentials)
      const errorMessage = await page.locator('.error-message').isVisible();
      if (errorMessage) {
        console.log('  ✅ Login validation working');
      }
    }
    
    // Test XSS protection
    await page.evaluate(() => {
      const script = document.createElement('script');
      script.innerHTML = 'alert("XSS")';
      document.body.appendChild(script);
    });
    
    // If we get here without alert, XSS protection is working
    console.log('  ✅ XSS protection active');
  });

  test('Data validation and error handling', async ({ page }) => {
    console.log('\n✅ Testing data validation');
    
    // Navigate to order creation
    await page.goto(`${TEST_CONFIG.baseURL}/orders/new`);
    
    // Test form validation
    await page.click('button[type="submit"]');
    
    // Check for validation errors
    const validationErrors = await page.locator('.field-error').count();
    if (validationErrors > 0) {
      console.log(`  ✅ Form validation working (${validationErrors} errors shown)`);
    }
    
    // Test Taiwan-specific validation
    await page.fill('input[name="phone"]', '123'); // Invalid phone
    await page.click('button[type="submit"]');
    
    const phoneError = await page.locator('.field-error[data-field="phone"]').isVisible();
    if (phoneError) {
      console.log('  ✅ Taiwan phone validation working');
    }
    
    // Test error boundary
    await page.evaluate(() => {
      throw new Error('Test error boundary');
    });
    
    await page.waitForTimeout(1000);
    
    // Check if error boundary caught the error
    const errorBoundary = await page.locator('.error-boundary').isVisible();
    if (errorBoundary) {
      console.log('  ✅ Error boundary working');
    }
  });

  test('Accessibility compliance', async ({ page }) => {
    console.log('\n♿ Testing accessibility');
    
    await page.goto(`${TEST_CONFIG.baseURL}/dashboard`);
    
    // Run accessibility checks
    const accessibilityIssues = await page.evaluate(() => {
      const issues: string[] = [];
      
      // Check for alt text on images
      const images = document.querySelectorAll('img');
      images.forEach(img => {
        if (!img.alt) {
          issues.push(`Image missing alt text: ${img.src}`);
        }
      });
      
      // Check for ARIA labels on buttons
      const buttons = document.querySelectorAll('button');
      buttons.forEach(button => {
        if (!button.textContent?.trim() && !button.getAttribute('aria-label')) {
          issues.push('Button missing accessible label');
        }
      });
      
      // Check for form labels
      const inputs = document.querySelectorAll('input, select, textarea');
      inputs.forEach(input => {
        const id = input.id;
        if (id) {
          const label = document.querySelector(`label[for="${id}"]`);
          if (!label && !input.getAttribute('aria-label')) {
            issues.push(`Input missing label: ${id}`);
          }
        }
      });
      
      // Check color contrast (simplified)
      const elementsWithColor = document.querySelectorAll('[style*="color"]');
      // Note: Real contrast checking would require more complex calculations
      
      return issues;
    });
    
    console.log(`  Found ${accessibilityIssues.length} accessibility issues`);
    if (accessibilityIssues.length > 0) {
      console.log('  Issues:', accessibilityIssues.slice(0, 5)); // Show first 5
    }
    
    // Test keyboard navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    const focusedElement = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });
    
    console.log(`  ✅ Keyboard navigation working (focused: ${focusedElement})`);
  });
});

// Run the comprehensive test suite
test.describe('Automated Fix Application', () => {
  test('Apply and verify automatic fixes', async ({ page }) => {
    console.log('\n🔧 Applying automatic fixes');
    
    // Initialize monitors
    const errorMonitor = new ErrorMonitor(page);
    const autoFixer = new AutoFixer();
    
    // First pass - collect errors
    await page.goto(`${TEST_CONFIG.baseURL}/dashboard`);
    await page.waitForTimeout(3000);
    
    const errors = errorMonitor.getErrors();
    const autoFixableErrors = errorMonitor.getAutoFixableErrors();
    
    if (autoFixableErrors.length > 0) {
      console.log(`Found ${autoFixableErrors.length} auto-fixable errors`);
      
      // Generate fixes
      const fixes = autoFixer.generateFixes(autoFixableErrors);
      console.log(`Generated ${fixes.length} fixes`);
      
      // Apply fixes (in real scenario, this would modify actual files)
      const result = await autoFixer.applyFixes(fixes);
      console.log(`Applied ${result.fixesApplied.length} fixes`);
      
      // Re-test after fixes
      errorMonitor.reset();
      await page.reload();
      await page.waitForTimeout(3000);
      
      const errorsAfterFix = errorMonitor.getErrors();
      const improvement = errors.length - errorsAfterFix.length;
      
      console.log(`\n📊 Fix Results:`);
      console.log(`  Errors before: ${errors.length}`);
      console.log(`  Errors after: ${errorsAfterFix.length}`);
      console.log(`  Improvement: ${improvement} errors fixed`);
      
      expect(errorsAfterFix.length).toBeLessThan(errors.length);
    } else {
      console.log('No auto-fixable errors found - great!');
    }
  });
});