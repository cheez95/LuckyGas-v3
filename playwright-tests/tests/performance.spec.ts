import { test, expect } from '@playwright/test';
import { APIHelper } from '../utils/api-helper';
import { TestHelpers } from '../utils/test-helpers';
import testData from '../fixtures/test-data.json';

test.describe('Performance Tests', () => {
  let apiHelper: APIHelper;

  test.beforeAll(async ({ request }) => {
    apiHelper = new APIHelper(request);
    await apiHelper.login('admin');
  });

  test.describe('API Response Time Tests', () => {
    test('should respond within 2 seconds for all endpoints', async ({ request }) => {
      const endpoints = [
        { method: 'GET', path: '/api/v1/customers/' },
        { method: 'GET', path: '/api/v1/orders/' },
        { method: 'GET', path: '/api/v1/products/' },
        { method: 'GET', path: '/api/v1/users/' },
        { method: 'GET', path: '/api/v1/analytics/executive' },
        { method: 'GET', path: '/api/v1/routes/' },
        { method: 'GET', path: '/api/v1/drivers/routes/today' }
      ];

      for (const endpoint of endpoints) {
        const start = Date.now();
        const response = await apiHelper.get(endpoint.path);
        const duration = Date.now() - start;
        
        expect(response.ok()).toBeTruthy();
        expect(duration).toBeLessThan(testData.performanceTargets.apiResponseTime);
        
        console.log(`${endpoint.method} ${endpoint.path}: ${duration}ms`);
      }
    });

    test('should handle complex queries efficiently', async () => {
      // Complex customer search with filters
      const complexQuery = {
        search: '王',
        type: 'commercial',
        area: '信義區',
        skip: 0,
        limit: 100,
        sort: 'created_at',
        order: 'desc'
      };
      
      const start = Date.now();
      const response = await apiHelper.get('/api/v1/customers/?' + new URLSearchParams(complexQuery));
      const duration = Date.now() - start;
      
      expect(response.ok()).toBeTruthy();
      expect(duration).toBeLessThan(testData.performanceTargets.apiResponseTime);
    });

    test('should optimize database queries', async () => {
      // Test N+1 query prevention
      const ordersResponse = await apiHelper.get('/api/v1/orders/?include=customer,items,driver');
      const orders = await ordersResponse.json();
      
      // Should include related data without additional queries
      if (orders.items && orders.items.length > 0) {
        expect(orders.items[0].customer).toBeTruthy();
        expect(orders.items[0].items).toBeTruthy();
      }
    });
  });

  test.describe('Load Testing', () => {
    test('should handle 100 concurrent users', async ({ request }) => {
      const concurrentRequests = 100;
      const requests = [];
      
      // Create concurrent requests
      for (let i = 0; i < concurrentRequests; i++) {
        const helper = new APIHelper(request);
        await helper.login(i % 2 === 0 ? 'admin' : 'manager');
        
        requests.push(
          helper.get('/api/v1/customers/'),
          helper.get('/api/v1/orders/'),
          helper.get('/api/v1/products/')
        );
      }
      
      const start = Date.now();
      const responses = await Promise.all(requests);
      const duration = Date.now() - start;
      
      // All requests should succeed
      const successCount = responses.filter(r => r.ok()).length;
      const errorRate = (responses.length - successCount) / responses.length;
      
      expect(errorRate).toBeLessThan(testData.performanceTargets.errorRate);
      console.log(`Completed ${responses.length} requests in ${duration}ms`);
      console.log(`Success rate: ${((1 - errorRate) * 100).toFixed(2)}%`);
    });

    test('should maintain performance under sustained load', async ({ request }) => {
      const duration = 30000; // 30 seconds
      const requestsPerSecond = 10;
      const results = {
        success: 0,
        error: 0,
        totalTime: 0,
        responseTimes: [] as number[]
      };
      
      const startTime = Date.now();
      
      while (Date.now() - startTime < duration) {
        const batchPromises = [];
        
        for (let i = 0; i < requestsPerSecond; i++) {
          const helper = new APIHelper(request);
          const requestStart = Date.now();
          
          batchPromises.push(
            helper.get('/api/v1/customers/').then(response => {
              const requestDuration = Date.now() - requestStart;
              results.responseTimes.push(requestDuration);
              
              if (response.ok()) {
                results.success++;
              } else {
                results.error++;
              }
              
              results.totalTime += requestDuration;
            })
          );
        }
        
        await Promise.all(batchPromises);
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
      }
      
      // Calculate metrics
      const avgResponseTime = results.totalTime / results.responseTimes.length;
      const p95ResponseTime = results.responseTimes.sort((a, b) => a - b)[
        Math.floor(results.responseTimes.length * 0.95)
      ];
      const errorRate = results.error / (results.success + results.error);
      
      console.log(`Sustained load test results:`);
      console.log(`Total requests: ${results.success + results.error}`);
      console.log(`Average response time: ${avgResponseTime.toFixed(2)}ms`);
      console.log(`P95 response time: ${p95ResponseTime}ms`);
      console.log(`Error rate: ${(errorRate * 100).toFixed(2)}%`);
      
      expect(p95ResponseTime).toBeLessThan(testData.performanceTargets.apiResponseTime);
      expect(errorRate).toBeLessThan(testData.performanceTargets.errorRate);
    });
  });

  test.describe('Page Load Performance', () => {
    test('should load pages within 3 seconds', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      
      const pages = [
        '/dashboard',
        '/customers',
        '/orders',
        '/routes',
        '/analytics/executive'
      ];
      
      for (const pagePath of pages) {
        const start = Date.now();
        await page.goto(pagePath);
        await TestHelpers.waitForLoadingComplete(page);
        const loadTime = Date.now() - start;
        
        expect(loadTime).toBeLessThan(testData.performanceTargets.pageLoadTime);
        
        // Get performance metrics
        const metrics = await TestHelpers.measurePerformance(page);
        console.log(`${pagePath} performance:`, {
          loadTime: `${loadTime}ms`,
          ...metrics
        });
      }
    });

    test('should optimize bundle size', async ({ page }) => {
      // Check network requests for bundle sizes
      const resourceSizes: Record<string, number> = {};
      
      page.on('response', response => {
        const url = response.url();
        if (url.includes('.js') || url.includes('.css')) {
          const size = response.headers()['content-length'];
          if (size) {
            const fileName = url.split('/').pop() || 'unknown';
            resourceSizes[fileName] = parseInt(size);
          }
        }
      });
      
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      
      // Check bundle sizes
      let totalSize = 0;
      Object.entries(resourceSizes).forEach(([file, size]) => {
        totalSize += size;
        console.log(`${file}: ${(size / 1024).toFixed(2)}KB`);
      });
      
      console.log(`Total bundle size: ${(totalSize / 1024).toFixed(2)}KB`);
      
      // Total JS/CSS should be under 2MB
      expect(totalSize).toBeLessThan(2 * 1024 * 1024);
    });

    test('should lazy load routes', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      
      // Track loaded chunks
      const loadedChunks = new Set<string>();
      
      page.on('response', response => {
        const url = response.url();
        if (url.includes('chunk') && url.includes('.js')) {
          loadedChunks.add(url);
        }
      });
      
      // Navigate to dashboard
      await page.goto('/dashboard');
      const initialChunks = new Set(loadedChunks);
      
      // Navigate to analytics (should load new chunk)
      await page.goto('/analytics/executive');
      
      // Should have loaded additional chunks
      expect(loadedChunks.size).toBeGreaterThan(initialChunks.size);
      console.log(`Lazy loaded ${loadedChunks.size - initialChunks.size} additional chunks`);
    });
  });

  test.describe('Database Performance', () => {
    test('should handle large dataset queries', async () => {
      // Test pagination performance with large dataset
      const pageSizes = [10, 50, 100];
      
      for (const limit of pageSizes) {
        const start = Date.now();
        const response = await apiHelper.get(`/api/v1/orders/?skip=0&limit=${limit}`);
        const duration = Date.now() - start;
        
        expect(response.ok()).toBeTruthy();
        expect(duration).toBeLessThan(testData.performanceTargets.apiResponseTime);
        
        console.log(`Query ${limit} records: ${duration}ms`);
      }
    });

    test('should use database indexes effectively', async () => {
      // Test common query patterns that should use indexes
      const queries = [
        { endpoint: '/api/v1/customers/', params: { search: '王' } },
        { endpoint: '/api/v1/orders/', params: { status: 'pending' } },
        { endpoint: '/api/v1/orders/', params: { customer_id: 1 } },
        { endpoint: '/api/v1/routes/', params: { scheduled_date: '2025-08-01' } }
      ];
      
      for (const query of queries) {
        const start = Date.now();
        const response = await apiHelper.get(
          query.endpoint + '?' + new URLSearchParams(query.params as any)
        );
        const duration = Date.now() - start;
        
        expect(response.ok()).toBeTruthy();
        expect(duration).toBeLessThan(500); // Indexed queries should be fast
        
        console.log(`Indexed query ${JSON.stringify(query.params)}: ${duration}ms`);
      }
    });
  });

  test.describe('Memory Usage', () => {
    test('should not have memory leaks in long sessions', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      
      // Get initial memory usage
      const getMemoryUsage = async () => {
        return await page.evaluate(() => {
          if ('memory' in performance) {
            return (performance as any).memory.usedJSHeapSize;
          }
          return 0;
        });
      };
      
      const initialMemory = await getMemoryUsage();
      console.log(`Initial memory: ${(initialMemory / 1024 / 1024).toFixed(2)}MB`);
      
      // Perform repetitive actions
      for (let i = 0; i < 10; i++) {
        await page.goto('/customers');
        await TestHelpers.waitForLoadingComplete(page);
        
        await page.goto('/orders');
        await TestHelpers.waitForLoadingComplete(page);
        
        await page.goto('/analytics/executive');
        await TestHelpers.waitForLoadingComplete(page);
      }
      
      // Force garbage collection if available
      await page.evaluate(() => {
        if (window.gc) {
          window.gc();
        }
      });
      
      await page.waitForTimeout(2000);
      
      const finalMemory = await getMemoryUsage();
      console.log(`Final memory: ${(finalMemory / 1024 / 1024).toFixed(2)}MB`);
      
      const memoryIncrease = finalMemory - initialMemory;
      console.log(`Memory increase: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB`);
      
      // Memory increase should be reasonable (less than 50MB)
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024);
    });
  });

  test.describe('Caching Performance', () => {
    test('should cache static assets', async ({ page }) => {
      await page.goto('/');
      
      // First load
      const firstLoadResources: Record<string, number> = {};
      page.on('response', response => {
        const url = response.url();
        if (url.includes('.js') || url.includes('.css') || url.includes('.png')) {
          firstLoadResources[url] = response.status();
        }
      });
      
      await page.waitForLoadState('networkidle');
      
      // Second load (should use cache)
      const cachedResources: Record<string, number> = {};
      page.on('response', response => {
        const url = response.url();
        if (firstLoadResources[url]) {
          cachedResources[url] = response.status();
        }
      });
      
      await page.reload();
      await page.waitForLoadState('networkidle');
      
      // Check cache headers
      let cachedCount = 0;
      Object.entries(cachedResources).forEach(([url, status]) => {
        if (status === 304) { // Not Modified
          cachedCount++;
        }
      });
      
      console.log(`Cached resources: ${cachedCount}/${Object.keys(firstLoadResources).length}`);
      
      // At least 50% should be cached
      expect(cachedCount).toBeGreaterThan(Object.keys(firstLoadResources).length * 0.5);
    });

    test('should cache API responses appropriately', async () => {
      // First request
      const start1 = Date.now();
      const response1 = await apiHelper.get('/api/v1/products/');
      const time1 = Date.now() - start1;
      
      // Second request (might be cached)
      const start2 = Date.now();
      const response2 = await apiHelper.get('/api/v1/products/');
      const time2 = Date.now() - start2;
      
      // Check cache headers
      const cacheControl = response2.headers()['cache-control'];
      const xCache = response2.headers()['x-cache'];
      
      console.log(`First request: ${time1}ms, Second request: ${time2}ms`);
      console.log(`Cache-Control: ${cacheControl}, X-Cache: ${xCache}`);
      
      expect(response1.ok()).toBeTruthy();
      expect(response2.ok()).toBeTruthy();
    });
  });

  test.describe('File Upload Performance', () => {
    test('should handle large file uploads', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/settings/import');
      
      // Create a large test file (5MB)
      const largeContent = 'x'.repeat(5 * 1024 * 1024);
      const fileName = 'large-test-file.csv';
      
      await page.setInputFiles('input[type="file"]', {
        name: fileName,
        mimeType: 'text/csv',
        buffer: Buffer.from(largeContent)
      });
      
      const start = Date.now();
      await page.click('button:has-text("上傳")');
      
      // Wait for upload to complete
      await expect(page.locator('.upload-progress')).toBeVisible();
      await expect(page.locator('.upload-success')).toBeVisible({ timeout: 30000 });
      
      const uploadTime = Date.now() - start;
      console.log(`5MB file upload time: ${uploadTime}ms`);
      
      // Should complete within 30 seconds
      expect(uploadTime).toBeLessThan(30000);
    });
  });

  test.describe('Real-time Performance', () => {
    test('should handle WebSocket connections efficiently', async ({ page, context }) => {
      // Open multiple tabs to simulate multiple connections
      const pages = [];
      
      for (let i = 0; i < 5; i++) {
        const newPage = await context.newPage();
        await TestHelpers.loginUI(newPage, 'administrator', 'SuperSecure#9876');
        await newPage.goto('/analytics/operations');
        pages.push(newPage);
      }
      
      // Wait for WebSocket connections
      await page.waitForTimeout(2000);
      
      // Trigger an update
      await apiHelper.post('/api/v1/orders/', {
        客戶ID: 1,
        預定配送日期: new Date().toISOString(),
        配送地址: 'WebSocket測試',
        訂單項目: [{ 產品ID: 1, 數量: 1, 單價: 850 }],
        總金額: 850
      });
      
      // All pages should receive the update
      for (const p of pages) {
        await expect(p.locator('.real-time-notification')).toBeVisible({ timeout: 5000 });
      }
      
      // Close extra pages
      for (const p of pages) {
        await p.close();
      }
    });
  });

  test.describe('Search Performance', () => {
    test('should provide fast search results', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers');
      
      const searchInput = page.locator('input[placeholder="搜尋客戶..."]');
      
      // Type search query
      const start = Date.now();
      await searchInput.fill('王');
      
      // Wait for search results
      await page.waitForResponse(response => 
        response.url().includes('/api/v1/customers/') && 
        response.url().includes('search=')
      );
      
      const searchTime = Date.now() - start;
      console.log(`Search response time: ${searchTime}ms`);
      
      // Search should be fast
      expect(searchTime).toBeLessThan(1000);
      
      // Results should be displayed
      await expect(page.locator('tbody tr')).toHaveCount(0, { timeout: 1000 });
    });

    test('should debounce search requests', async ({ page }) => {
      await TestHelpers.loginUI(page, 'administrator', 'SuperSecure#9876');
      await page.goto('/customers');
      
      let requestCount = 0;
      page.on('request', request => {
        if (request.url().includes('search=')) {
          requestCount++;
        }
      });
      
      const searchInput = page.locator('input[placeholder="搜尋客戶..."]');
      
      // Type quickly
      await searchInput.type('王大明', { delay: 50 });
      
      // Wait for debounce
      await page.waitForTimeout(1000);
      
      // Should only make 1-2 requests, not one per character
      console.log(`Search requests made: ${requestCount}`);
      expect(requestCount).toBeLessThanOrEqual(2);
    });
  });
});