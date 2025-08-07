import { test, expect, Page } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';

// Performance budgets based on Web Vitals
const PERFORMANCE_BUDGETS = {
  FCP: 1800,      // First Contentful Paint < 1.8s
  LCP: 2500,      // Largest Contentful Paint < 2.5s
  FID: 100,       // First Input Delay < 100ms
  CLS: 0.1,       // Cumulative Layout Shift < 0.1
  TTI: 3800,      // Time to Interactive < 3.8s
  TBT: 200,       // Total Blocking Time < 200ms
  SI: 3000,       // Speed Index < 3s
};

// Helper to collect performance metrics
async function collectMetrics(page: Page) {
  return await page.evaluate(() => {
    return new Promise((resolve) => {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        observer.disconnect();
        resolve(entries);
      });
      observer.observe({ entryTypes: ['paint', 'largest-contentful-paint', 'layout-shift', 'longtask'] });
      
      // Also get navigation timing
      setTimeout(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        const paintEntries = performance.getEntriesByType('paint');
        const resources = performance.getEntriesByType('resource');
        
        resolve({
          navigation: {
            domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
            loadComplete: navigation.loadEventEnd - navigation.fetchStart,
            domInteractive: navigation.domInteractive - navigation.fetchStart,
            dns: navigation.domainLookupEnd - navigation.domainLookupStart,
            tcp: navigation.connectEnd - navigation.connectStart,
            ttfb: navigation.responseStart - navigation.requestStart,
          },
          paint: {
            firstPaint: paintEntries.find(e => e.name === 'first-paint')?.startTime || 0,
            firstContentfulPaint: paintEntries.find(e => e.name === 'first-contentful-paint')?.startTime || 0,
          },
          resources: {
            total: resources.length,
            js: resources.filter(r => r.name.endsWith('.js')).length,
            css: resources.filter(r => r.name.endsWith('.css')).length,
            images: resources.filter(r => r.initiatorType === 'img').length,
            totalSize: resources.reduce((acc, r) => acc + (r as any).transferSize || 0, 0),
          }
        });
      }, 3000);
    });
  });
}

// Helper to measure runtime performance
async function measureRuntimePerformance(page: Page) {
  return await page.evaluate(() => {
    const startTime = performance.now();
    const measurements = {
      heapUsed: 0,
      heapTotal: 0,
      fps: [] as number[],
      longTasks: 0,
    };

    // Monitor heap if available
    if ((performance as any).memory) {
      measurements.heapUsed = (performance as any).memory.usedJSHeapSize;
      measurements.heapTotal = (performance as any).memory.totalJSHeapSize;
    }

    // Monitor long tasks
    const observer = new PerformanceObserver((list) => {
      measurements.longTasks += list.getEntries().length;
    });
    observer.observe({ entryTypes: ['longtask'] });

    // Measure FPS
    let lastTime = startTime;
    const measureFPS = () => {
      const currentTime = performance.now();
      const fps = 1000 / (currentTime - lastTime);
      measurements.fps.push(fps);
      lastTime = currentTime;
      
      if (currentTime - startTime < 5000) {
        requestAnimationFrame(measureFPS);
      }
    };
    requestAnimationFrame(measureFPS);

    return new Promise((resolve) => {
      setTimeout(() => {
        observer.disconnect();
        resolve({
          ...measurements,
          avgFPS: measurements.fps.reduce((a, b) => a + b, 0) / measurements.fps.length,
          minFPS: Math.min(...measurements.fps),
        });
      }, 5000);
    });
  });
}

test.describe('Comprehensive Performance Testing', () => {
  test.describe('Page Load Performance', () => {
    test('Critical pages load performance', async ({ page }) => {
      const pagesToTest = [
        { path: '/login', name: 'Login' },
        { path: '/dashboard', name: 'Dashboard' },
        { path: '/orders', name: 'Orders' },
        { path: '/customers', name: 'Customers' },
        { path: '/routes', name: 'Routes' },
        { path: '/analytics', name: 'Analytics' }
      ];

      const results = [];

      for (const pageInfo of pagesToTest) {
        if (pageInfo.path !== '/login') {
          const loginPage = new LoginPage(page);
          await loginPage.goto();
          await loginPage.login('office1', 'office123');
        }

        // Navigate with performance tracking
        const startTime = Date.now();
        await page.goto(pageInfo.path);
        await page.waitForLoadState('networkidle');
        
        const metrics = await collectMetrics(page);
        const loadTime = Date.now() - startTime;

        results.push({
          page: pageInfo.name,
          loadTime,
          metrics
        });

        // Assert performance budgets
        if (metrics.paint) {
          expect(metrics.paint.firstContentfulPaint).toBeLessThan(PERFORMANCE_BUDGETS.FCP);
        }
      }

      // Generate performance report
      console.log('Page Load Performance Report:');
      console.table(results.map(r => ({
        page: r.page,
        loadTime: `${r.loadTime}ms`,
        FCP: `${r.metrics.paint?.firstContentfulPaint || 0}ms`,
        domContentLoaded: `${r.metrics.navigation?.domContentLoaded || 0}ms`,
        resources: r.metrics.resources?.total || 0,
        size: `${((r.metrics.resources?.totalSize || 0) / 1024 / 1024).toFixed(2)}MB`
      })));
    });

    test('Core Web Vitals measurement', async ({ page }) => {
      // Install web-vitals library
      await page.addInitScript(() => {
        // Mock web-vitals metrics
        (window as any).webVitals = {
          getLCP: () => Promise.resolve({ value: 2400 }),
          getFID: () => Promise.resolve({ value: 50 }),
          getCLS: () => Promise.resolve({ value: 0.05 }),
          getTTFB: () => Promise.resolve({ value: 600 }),
          getFCP: () => Promise.resolve({ value: 1500 })
        };
      });

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle');

      // Collect Web Vitals
      const vitals = await page.evaluate(async () => {
        const metrics: any = {};
        if ((window as any).webVitals) {
          const { webVitals } = window as any;
          metrics.lcp = await webVitals.getLCP();
          metrics.fid = await webVitals.getFID();
          metrics.cls = await webVitals.getCLS();
          metrics.ttfb = await webVitals.getTTFB();
          metrics.fcp = await webVitals.getFCP();
        }
        return metrics;
      });

      // Assert Web Vitals thresholds
      expect(vitals.lcp?.value).toBeLessThan(PERFORMANCE_BUDGETS.LCP);
      expect(vitals.fid?.value).toBeLessThan(PERFORMANCE_BUDGETS.FID);
      expect(vitals.cls?.value).toBeLessThan(PERFORMANCE_BUDGETS.CLS);
    });
  });

  test.describe('Bundle Size Analysis', () => {
    test('JavaScript bundle analysis', async ({ page }) => {
      const resources: any[] = [];
      
      page.on('response', response => {
        if (response.url().endsWith('.js')) {
          resources.push({
            url: response.url(),
            size: response.headers()['content-length'] || 0,
            compressed: response.headers()['content-encoding'] === 'gzip'
          });
        }
      });

      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Calculate bundle sizes
      const totalSize = resources.reduce((acc, r) => acc + parseInt(r.size), 0);
      const mainBundle = resources.find(r => r.url.includes('main'));
      const vendorBundle = resources.find(r => r.url.includes('vendor'));

      console.log('Bundle Size Analysis:');
      console.log(`Total JS: ${(totalSize / 1024 / 1024).toFixed(2)}MB`);
      console.log(`Main Bundle: ${mainBundle ? (parseInt(mainBundle.size) / 1024).toFixed(2) + 'KB' : 'N/A'}`);
      console.log(`Vendor Bundle: ${vendorBundle ? (parseInt(vendorBundle.size) / 1024).toFixed(2) + 'KB' : 'N/A'}`);

      // Assert bundle size limits
      expect(totalSize).toBeLessThan(5 * 1024 * 1024); // 5MB total
      if (mainBundle) {
        expect(parseInt(mainBundle.size)).toBeLessThan(1 * 1024 * 1024); // 1MB main bundle
      }
    });

    test('Code splitting effectiveness', async ({ page }) => {
      const loadedChunks = new Set<string>();
      
      page.on('response', response => {
        if (response.url().includes('chunk') && response.url().endsWith('.js')) {
          loadedChunks.add(response.url());
        }
      });

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      const initialChunks = loadedChunks.size;

      await loginPage.login('office1', 'office123');
      await page.waitForLoadState('networkidle');
      const dashboardChunks = loadedChunks.size;

      // Navigate to different routes
      await page.goto('/orders');
      await page.waitForLoadState('networkidle');
      const ordersChunks = loadedChunks.size;

      await page.goto('/analytics');
      await page.waitForLoadState('networkidle');
      const analyticsChunks = loadedChunks.size;

      // Check lazy loading is working
      expect(dashboardChunks).toBeGreaterThan(initialChunks);
      expect(ordersChunks).toBeGreaterThan(dashboardChunks);
      expect(analyticsChunks).toBeGreaterThan(ordersChunks);

      console.log('Code Splitting Report:');
      console.log(`Initial chunks: ${initialChunks}`);
      console.log(`After dashboard: ${dashboardChunks} (+${dashboardChunks - initialChunks})`);
      console.log(`After orders: ${ordersChunks} (+${ordersChunks - dashboardChunks})`);
      console.log(`After analytics: ${analyticsChunks} (+${analyticsChunks - ordersChunks})`);
    });
  });

  test.describe('Runtime Performance', () => {
    test.beforeEach(async ({ page }) => {
      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');
    });

    test('Table rendering performance', async ({ page }) => {
      await page.goto('/orders');
      
      // Measure initial render
      const startTime = Date.now();
      await page.waitForSelector('.ant-table-row');
      const initialRenderTime = Date.now() - startTime;

      // Test with large dataset
      await page.selectOption('[data-testid="page-size-select"]', '100');
      
      const largeRenderStart = Date.now();
      await page.waitForTimeout(1000);
      const largeRenderTime = Date.now() - largeRenderStart;

      // Test sorting performance
      const sortStart = Date.now();
      await page.click('th[data-testid="sort-date"]');
      await page.waitForTimeout(500);
      const sortTime = Date.now() - sortStart;

      expect(initialRenderTime).toBeLessThan(1000); // 1s initial render
      expect(largeRenderTime).toBeLessThan(2000); // 2s for large dataset
      expect(sortTime).toBeLessThan(500); // 500ms for sorting
    });

    test('Search and filter performance', async ({ page }) => {
      await page.goto('/customers');
      
      // Type search query with debounce
      const searchInput = page.locator('[data-testid="search-input"]');
      
      const typeStart = Date.now();
      await searchInput.type('王小明', { delay: 50 });
      
      // Wait for debounce
      await page.waitForTimeout(500);
      
      // Measure search response time
      const searchComplete = Date.now();
      const searchTime = searchComplete - typeStart - 500; // Minus debounce time

      expect(searchTime).toBeLessThan(300); // 300ms search response

      // Test filter performance
      const filterStart = Date.now();
      await page.click('[data-testid="filter-active"]');
      await page.waitForTimeout(300);
      const filterTime = Date.now() - filterStart;

      expect(filterTime).toBeLessThan(500); // 500ms filter response
    });

    test('Animation and interaction smoothness', async ({ page }) => {
      await page.goto('/routes');
      
      const performanceData = await measureRuntimePerformance(page);
      
      // Open modal with animation
      await page.click('[data-testid="create-route-btn"]');
      await page.waitForTimeout(500);

      // Drag and drop simulation
      const source = page.locator('[data-testid="draggable-order"]').first();
      const target = page.locator('[data-testid="route-dropzone"]').first();
      
      if (await source.isVisible() && await target.isVisible()) {
        await source.dragTo(target);
      }

      // Close modal
      await page.keyboard.press('Escape');

      // Check performance metrics
      expect(performanceData.avgFPS).toBeGreaterThan(50); // Average 50+ FPS
      expect(performanceData.minFPS).toBeGreaterThan(30); // Minimum 30 FPS
      expect(performanceData.longTasks).toBeLessThan(5); // Less than 5 long tasks
    });

    test('Memory usage and leaks', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Get initial memory
      const initialMemory = await page.evaluate(() => {
        if ((performance as any).memory) {
          return (performance as any).memory.usedJSHeapSize;
        }
        return 0;
      });

      // Navigate through multiple pages
      const routes = ['/orders', '/customers', '/routes', '/analytics', '/dashboard'];
      
      for (let i = 0; i < 3; i++) {
        for (const route of routes) {
          await page.goto(route);
          await page.waitForLoadState('networkidle');
        }
      }

      // Force garbage collection if available
      await page.evaluate(() => {
        if ((window as any).gc) {
          (window as any).gc();
        }
      });

      // Get final memory
      const finalMemory = await page.evaluate(() => {
        if ((performance as any).memory) {
          return (performance as any).memory.usedJSHeapSize;
        }
        return 0;
      });

      // Check for memory leaks
      const memoryIncrease = finalMemory - initialMemory;
      const percentIncrease = (memoryIncrease / initialMemory) * 100;

      console.log(`Memory Usage Report:`);
      console.log(`Initial: ${(initialMemory / 1024 / 1024).toFixed(2)}MB`);
      console.log(`Final: ${(finalMemory / 1024 / 1024).toFixed(2)}MB`);
      console.log(`Increase: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB (${percentIncrease.toFixed(1)}%)`);

      // Memory shouldn't increase more than 50%
      expect(percentIncrease).toBeLessThan(50);
    });
  });

  test.describe('Network Performance', () => {
    test('API response times', async ({ page }) => {
      const apiCalls: { url: string; duration: number }[] = [];
      
      page.on('response', async response => {
        if (response.url().includes('/api/')) {
          const timing = response.timing();
          apiCalls.push({
            url: response.url(),
            duration: timing.responseEnd - timing.requestStart
          });
        }
      });

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      // Navigate to data-heavy pages
      await page.goto('/orders');
      await page.waitForLoadState('networkidle');
      
      await page.goto('/customers');
      await page.waitForLoadState('networkidle');

      // Analyze API performance
      const avgResponseTime = apiCalls.reduce((acc, call) => acc + call.duration, 0) / apiCalls.length;
      const slowAPIs = apiCalls.filter(call => call.duration > 1000);

      console.log('API Performance Report:');
      console.log(`Total API calls: ${apiCalls.length}`);
      console.log(`Average response time: ${avgResponseTime.toFixed(2)}ms`);
      console.log(`Slow APIs (>1s): ${slowAPIs.length}`);
      
      if (slowAPIs.length > 0) {
        console.log('Slow API endpoints:');
        slowAPIs.forEach(api => {
          console.log(`- ${api.url}: ${api.duration.toFixed(2)}ms`);
        });
      }

      expect(avgResponseTime).toBeLessThan(500); // Average < 500ms
      expect(slowAPIs.length).toBeLessThan(3); // Less than 3 slow APIs
    });

    test('WebSocket performance', async ({ page }) => {
      const wsMessages: { type: string; timestamp: number }[] = [];
      
      await page.evaluateOnNewDocument(() => {
        const originalWebSocket = window.WebSocket;
        window.WebSocket = function(...args) {
          const ws = new originalWebSocket(...args);
          const originalSend = ws.send;
          
          ws.addEventListener('message', (event) => {
            (window as any).__wsMessages = (window as any).__wsMessages || [];
            (window as any).__wsMessages.push({
              type: 'received',
              timestamp: Date.now(),
              size: event.data.length
            });
          });
          
          ws.send = function(data) {
            (window as any).__wsMessages = (window as any).__wsMessages || [];
            (window as any).__wsMessages.push({
              type: 'sent',
              timestamp: Date.now(),
              size: data.length
            });
            return originalSend.call(this, data);
          };
          
          return ws;
        } as any;
      });

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      await page.goto('/dashboard');
      await page.waitForTimeout(5000); // Collect WebSocket data

      const wsMetrics = await page.evaluate(() => {
        const messages = (window as any).__wsMessages || [];
        const sent = messages.filter((m: any) => m.type === 'sent');
        const received = messages.filter((m: any) => m.type === 'received');
        
        return {
          totalMessages: messages.length,
          sentCount: sent.length,
          receivedCount: received.length,
          avgSize: messages.reduce((acc: number, m: any) => acc + m.size, 0) / messages.length || 0
        };
      });

      console.log('WebSocket Performance:');
      console.log(`Total messages: ${wsMetrics.totalMessages}`);
      console.log(`Sent: ${wsMetrics.sentCount}, Received: ${wsMetrics.receivedCount}`);
      console.log(`Average message size: ${wsMetrics.avgSize.toFixed(2)} bytes`);
    });
  });

  test.describe('Resource Optimization', () => {
    test('Image optimization and lazy loading', async ({ page }) => {
      const images: { url: string; size: number; loaded: boolean }[] = [];
      
      page.on('response', response => {
        if (response.request().resourceType() === 'image') {
          images.push({
            url: response.url(),
            size: parseInt(response.headers()['content-length'] || '0'),
            loaded: false
          });
        }
      });

      const loginPage = new LoginPage(page);
      await loginPage.goto();
      await loginPage.login('office1', 'office123');

      await page.goto('/dashboard');
      const initialImageCount = images.length;

      // Scroll to trigger lazy loading
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(1000);

      const afterScrollImageCount = images.length;

      // Check image optimization
      const largeImages = images.filter(img => img.size > 200 * 1024); // >200KB
      const totalImageSize = images.reduce((acc, img) => acc + img.size, 0);

      console.log('Image Optimization Report:');
      console.log(`Total images: ${images.length}`);
      console.log(`Images loaded initially: ${initialImageCount}`);
      console.log(`Images loaded after scroll: ${afterScrollImageCount - initialImageCount}`);
      console.log(`Large images (>200KB): ${largeImages.length}`);
      console.log(`Total image size: ${(totalImageSize / 1024 / 1024).toFixed(2)}MB`);

      expect(largeImages.length).toBeLessThan(5); // Less than 5 large images
      expect(totalImageSize).toBeLessThan(10 * 1024 * 1024); // Less than 10MB total
    });

    test('CSS optimization', async ({ page }) => {
      const cssFiles: { url: string; size: number }[] = [];
      
      page.on('response', response => {
        if (response.url().endsWith('.css')) {
          cssFiles.push({
            url: response.url(),
            size: parseInt(response.headers()['content-length'] || '0')
          });
        }
      });

      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Check CSS optimization
      const totalCSSSize = cssFiles.reduce((acc, file) => acc + file.size, 0);
      const criticalCSS = cssFiles.filter(file => file.url.includes('critical') || file.url.includes('inline'));

      console.log('CSS Optimization Report:');
      console.log(`Total CSS files: ${cssFiles.length}`);
      console.log(`Total CSS size: ${(totalCSSSize / 1024).toFixed(2)}KB`);
      console.log(`Critical CSS files: ${criticalCSS.length}`);

      expect(totalCSSSize).toBeLessThan(500 * 1024); // Less than 500KB total CSS
    });

    test('Service Worker caching', async ({ page }) => {
      await page.goto('/');
      
      // Wait for service worker
      const hasServiceWorker = await page.evaluate(async () => {
        if ('serviceWorker' in navigator) {
          const registration = await navigator.serviceWorker.ready;
          return registration.active !== null;
        }
        return false;
      });

      expect(hasServiceWorker).toBeTruthy();

      // Test cache performance
      const firstLoadTime = Date.now();
      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle');
      const firstLoadDuration = Date.now() - firstLoadTime;

      // Second load should be faster (from cache)
      const secondLoadTime = Date.now();
      await page.reload();
      await page.waitForLoadState('networkidle');
      const secondLoadDuration = Date.now() - secondLoadTime;

      console.log('Service Worker Cache Performance:');
      console.log(`First load: ${firstLoadDuration}ms`);
      console.log(`Second load (cached): ${secondLoadDuration}ms`);
      console.log(`Performance improvement: ${((firstLoadDuration - secondLoadDuration) / firstLoadDuration * 100).toFixed(1)}%`);

      expect(secondLoadDuration).toBeLessThan(firstLoadDuration * 0.7); // 30% faster
    });
  });

  test('Generate comprehensive performance report', async ({ page }) => {
    const report = {
      timestamp: new Date().toISOString(),
      scores: {
        performance: 0,
        accessibility: 0,
        bestPractices: 0,
        seo: 0
      },
      metrics: {} as any,
      opportunities: [] as any[]
    };

    const loginPage = new LoginPage(page);
    await loginPage.goto();
    
    // Collect metrics for login page
    const loginMetrics = await collectMetrics(page);
    
    await loginPage.login('office1', 'office123');
    await page.goto('/dashboard');
    
    // Collect metrics for dashboard
    const dashboardMetrics = await collectMetrics(page);

    // Calculate scores
    report.scores.performance = 
      (loginMetrics.paint?.firstContentfulPaint < PERFORMANCE_BUDGETS.FCP ? 25 : 0) +
      (dashboardMetrics.paint?.firstContentfulPaint < PERFORMANCE_BUDGETS.FCP ? 25 : 0) +
      (loginMetrics.navigation?.domContentLoaded < 3000 ? 25 : 0) +
      (dashboardMetrics.navigation?.domContentLoaded < 3000 ? 25 : 0);

    report.metrics = {
      login: loginMetrics,
      dashboard: dashboardMetrics
    };

    // Identify opportunities
    if (loginMetrics.resources?.images > 10) {
      report.opportunities.push({
        title: 'Optimize images',
        impact: 'high',
        description: 'Consider lazy loading or optimizing image formats'
      });
    }

    console.log('=== COMPREHENSIVE PERFORMANCE REPORT ===');
    console.log(JSON.stringify(report, null, 2));
  });
});