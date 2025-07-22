import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test('should load dashboard within 3 seconds', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    // Measure dashboard load time
    const startTime = Date.now();
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;
    
    expect(loadTime).toBeLessThan(3000);
    
    // Check Core Web Vitals
    const metrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        let fcp, lcp;
        
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (entry.name === 'first-contentful-paint') {
              fcp = entry.startTime;
            }
          });
        }).observe({ entryTypes: ['paint'] });
        
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          lcp = entries[entries.length - 1].startTime;
          resolve({ fcp, lcp });
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        // Timeout after 5 seconds
        setTimeout(() => resolve({ fcp, lcp }), 5000);
      });
    });
    
    // Check performance metrics
    expect(metrics.fcp).toBeLessThan(1500); // FCP < 1.5s
    expect(metrics.lcp).toBeLessThan(2500); // LCP < 2.5s
  });

  test('should handle large customer list efficiently', async ({ page }) => {
    await page.goto('/login');
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    // Navigate to customers
    await page.goto('/customers');
    
    // Measure table render time
    const startTime = Date.now();
    await page.waitForSelector('.ant-table-tbody tr');
    const renderTime = Date.now() - startTime;
    
    expect(renderTime).toBeLessThan(1000); // Table should render within 1 second
    
    // Check scroll performance
    await page.evaluate(() => {
      const table = document.querySelector('.ant-table-body');
      if (table) {
        table.scrollTop = table.scrollHeight;
      }
    });
    
    // Should maintain smooth scrolling
    const scrollPerformance = await page.evaluate(() => {
      return new Promise((resolve) => {
        let frameCount = 0;
        let lastTime = performance.now();
        
        function checkFrame() {
          frameCount++;
          const currentTime = performance.now();
          
          if (currentTime - lastTime >= 1000) {
            resolve(frameCount);
          } else {
            requestAnimationFrame(checkFrame);
          }
        }
        
        requestAnimationFrame(checkFrame);
      });
    });
    
    expect(scrollPerformance).toBeGreaterThan(30); // Should maintain >30 FPS
  });

  test('should optimize bundle size', async ({ page }) => {
    const response = await page.goto('/');
    const resources = await page.evaluate(() => 
      performance.getEntriesByType('resource').map(r => ({
        name: r.name,
        size: r.transferSize,
        type: r.initiatorType
      }))
    );
    
    // Check main bundle size
    const jsBundles = resources.filter(r => r.type === 'script');
    const totalJsSize = jsBundles.reduce((sum, bundle) => sum + bundle.size, 0);
    
    expect(totalJsSize).toBeLessThan(1024 * 1024); // Total JS < 1MB
    
    // Check CSS bundle size
    const cssBundles = resources.filter(r => r.type === 'link' && r.name.includes('.css'));
    const totalCssSize = cssBundles.reduce((sum, bundle) => sum + bundle.size, 0);
    
    expect(totalCssSize).toBeLessThan(200 * 1024); // Total CSS < 200KB
  });

  test('should handle concurrent WebSocket connections', async ({ page, context }) => {
    // Open multiple tabs
    const pages = await Promise.all([
      context.newPage(),
      context.newPage(),
      context.newPage()
    ]);
    
    // Login on all pages
    for (const p of pages) {
      await p.goto('/login');
      await p.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
      await p.getByPlaceholder('密碼').fill('Admin123!');
      await p.getByRole('button', { name: '登入' }).click();
      await expect(p).toHaveURL(/.*dashboard/);
    }
    
    // Check WebSocket connections on all pages
    for (const p of pages) {
      const wsStatus = await p.evaluate(() => {
        return window.wsConnection?.readyState === 1;
      });
      expect(wsStatus).toBe(true);
    }
    
    // Clean up
    for (const p of pages) {
      await p.close();
    }
  });

  test('should cache static assets', async ({ page }) => {
    // First visit
    await page.goto('/login');
    
    // Get initial resource timings
    const initialResources = await page.evaluate(() => 
      performance.getEntriesByType('resource').map(r => ({
        name: r.name,
        duration: r.duration
      }))
    );
    
    // Reload page
    await page.reload();
    
    // Get cached resource timings
    const cachedResources = await page.evaluate(() => 
      performance.getEntriesByType('resource').map(r => ({
        name: r.name,
        duration: r.duration,
        cached: r.transferSize === 0
      }))
    );
    
    // Check that static assets are cached
    const cachedAssets = cachedResources.filter(r => 
      r.cached && (r.name.includes('.js') || r.name.includes('.css') || r.name.includes('.png'))
    );
    
    expect(cachedAssets.length).toBeGreaterThan(0);
  });

  test('should handle API errors gracefully', async ({ page }) => {
    await page.goto('/login');
    
    // Intercept API calls to simulate errors
    await page.route('**/api/v1/**', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });
    
    // Try to login
    await page.getByPlaceholder('電子郵件').fill('admin@luckygas.tw');
    await page.getByPlaceholder('密碼').fill('Admin123!');
    await page.getByRole('button', { name: '登入' }).click();
    
    // Should show error message, not crash
    await expect(page.locator('.ant-message-error')).toBeVisible();
    await expect(page).toHaveURL(/.*login/); // Should stay on login page
  });

  test('should optimize image loading', async ({ page }) => {
    await page.goto('/');
    
    // Check for lazy loaded images
    const images = await page.evaluate(() => {
      const imgs = Array.from(document.querySelectorAll('img'));
      return imgs.map(img => ({
        src: img.src,
        loading: img.loading,
        decoding: img.decoding
      }));
    });
    
    // Images should use lazy loading
    const lazyImages = images.filter(img => img.loading === 'lazy');
    expect(lazyImages.length).toBeGreaterThan(0);
  });
});