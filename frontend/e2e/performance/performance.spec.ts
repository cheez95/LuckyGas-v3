import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../helpers/auth.helper';

test.describe('Performance Benchmarks', () => {
  test('should meet performance benchmarks', async ({ page }) => {
    const startTime = Date.now();
    
    // Navigate to the app
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // Performance assertion
    expect(loadTime).toBeLessThan(3000); // 3 second budget
    
    // Capture performance metrics
    const performanceMetrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0
      };
    });
    
    // Log metrics for debugging
    console.log('Initial Load Metrics:', performanceMetrics);
    
    // Verify critical metrics
    expect(performanceMetrics.firstContentfulPaint).toBeLessThan(1500); // FCP < 1.5s
  });

  test('should meet performance benchmarks - 2', async ({ page }) => {
    // Measure login to dashboard time
    await page.goto('http://localhost:5173');
    
    const loginStartTime = Date.now();
    
    // Perform login
    await page.fill('input[placeholder*="用戶名"]', 'test@example.com');
    await page.fill('input[placeholder*="密碼"]', 'test123');
    await page.click('button:has-text("登 入")');
    
    // Wait for dashboard
    await page.waitForURL(/dashboard/);
    await page.waitForLoadState('networkidle');
    
    const dashboardLoadTime = Date.now() - loginStartTime;
    
    // Dashboard should load quickly after login
    expect(dashboardLoadTime).toBeLessThan(5000); // 5 second budget for login + dashboard
    
    // Measure Core Web Vitals
    const webVitals = await page.evaluate(() => {
      return new Promise((resolve) => {
        let lcp = 0;
        let fid = 0;
        let cls = 0;
        
        // Observe LCP
        new PerformanceObserver((entryList) => {
          const entries = entryList.getEntries();
          lcp = entries[entries.length - 1].startTime;
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        // Observe FID (First Input Delay)
        new PerformanceObserver((entryList) => {
          const entries = entryList.getEntries();
          if (entries.length > 0) {
            fid = entries[0].processingStart - entries[0].startTime;
          }
        }).observe({ entryTypes: ['first-input'] });
        
        // Observe CLS
        new PerformanceObserver((entryList) => {
          const entries = entryList.getEntries();
          entries.forEach(entry => {
            if (entry.hadRecentInput) return;
            cls += entry.value;
          });
        }).observe({ entryTypes: ['layout-shift'] });
        
        // Wait a bit to collect metrics
        setTimeout(() => {
          resolve({ lcp, fid, cls });
        }, 2000);
      });
    });
    
    console.log('Core Web Vitals:', webVitals);
    
    // Assert Core Web Vitals thresholds
    expect(webVitals.lcp).toBeLessThan(2500); // LCP < 2.5s (Good)
    expect(webVitals.cls).toBeLessThan(0.1);  // CLS < 0.1 (Good)
  });

  test('API response times', async ({ page, request }) => {
    await loginAsTestUser(page);
    
    // Measure API response times
    const apiEndpoints = [
      '/api/v1/customers',
      '/api/v1/orders',
      '/api/v1/products',
      '/api/v1/predictions/summary'
    ];
    
    const apiMetrics: { endpoint: string; responseTime: number; status: number }[] = [];
    
    // Set up request interception
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/v1/')) {
        const timing = response.timing();
        if (timing) {
          apiMetrics.push({
            endpoint: url.substring(url.indexOf('/api/v1/')),
            responseTime: timing.responseEnd,
            status: response.status()
          });
        }
      }
    });
    
    // Navigate to trigger API calls
    await page.click('text=客戶管理');
    await page.waitForLoadState('networkidle');
    
    await page.click('text=訂單管理');
    await page.waitForLoadState('networkidle');
    
    // Analyze API metrics
    console.log('API Response Times:', apiMetrics);
    
    // Assert API performance
    apiMetrics.forEach(metric => {
      expect(metric.responseTime).toBeLessThan(1000); // All APIs should respond < 1s
      expect(metric.status).toBe(200); // All should be successful
    });
    
    // Calculate average response time
    if (apiMetrics.length > 0) {
      const avgResponseTime = apiMetrics.reduce((sum, m) => sum + m.responseTime, 0) / apiMetrics.length;
      expect(avgResponseTime).toBeLessThan(500); // Average should be < 500ms
    }
  });

  test('should meet performance benchmarks - 3', async ({ page }) => {
    await loginAsTestUser(page);
    
    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
    
    // Perform multiple navigations to test for memory leaks
    const pages = ['客戶管理', '訂單管理', '路線規劃', '儀表板'];
    
    for (let i = 0; i < 3; i++) {
      for (const pageName of pages) {
        await page.click(`text=${pageName}`);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);
      }
    }
    
    // Force garbage collection if available
    await page.evaluate(() => {
      if (window.gc) {
        window.gc();
      }
    });
    
    // Get final memory usage
    const finalMemory = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory.usedJSHeapSize;
      }
      return 0;
    });
    
    if (initialMemory > 0 && finalMemory > 0) {
      const memoryIncrease = finalMemory - initialMemory;
      const increasePercentage = (memoryIncrease / initialMemory) * 100;
      
      console.log('Memory Usage:', {
        initial: `${(initialMemory / 1024 / 1024).toFixed(2)} MB`,
        final: `${(finalMemory / 1024 / 1024).toFixed(2)} MB`,
        increase: `${(memoryIncrease / 1024 / 1024).toFixed(2)} MB (${increasePercentage.toFixed(2)}%)`
      });
      
      // Memory increase should be reasonable (less than 50% increase)
      expect(increasePercentage).toBeLessThan(50);
    }
  });

  test('should meet performance benchmarks - 4', async ({ page }) => {
    // Navigate to the app
    await page.goto('http://localhost:5173');
    
    // Get all loaded resources
    const resources = await page.evaluate(() => {
      return performance.getEntriesByType('resource').map(entry => ({
        name: entry.name,
        size: entry.transferSize,
        type: entry.initiatorType
      }));
    });
    
    // Filter JavaScript bundles
    const jsBundles = resources.filter(r => r.name.includes('.js') && r.type === 'script');
    const totalJsSize = jsBundles.reduce((sum, bundle) => sum + bundle.size, 0);
    
    // Filter CSS bundles
    const cssBundles = resources.filter(r => r.name.includes('.css') && r.type === 'link');
    const totalCssSize = cssBundles.reduce((sum, bundle) => sum + bundle.size, 0);
    
    console.log('Bundle Sizes:', {
      totalJs: `${(totalJsSize / 1024).toFixed(2)} KB`,
      totalCss: `${(totalCssSize / 1024).toFixed(2)} KB`,
      total: `${((totalJsSize + totalCssSize) / 1024).toFixed(2)} KB`
    });
    
    // Assert bundle size limits
    expect(totalJsSize).toBeLessThan(500 * 1024); // JS < 500KB
    expect(totalCssSize).toBeLessThan(100 * 1024); // CSS < 100KB
    expect(totalJsSize + totalCssSize).toBeLessThan(600 * 1024); // Total < 600KB
  });

  test('Concurrent user simulation', async ({ browser }) => {
    const userCount = 5;
    const contexts = [];
    const pages = [];
    
    // Create multiple browser contexts to simulate concurrent users
    for (let i = 0; i < userCount; i++) {
      const context = await browser.newContext();
      const page = await context.newPage();
      contexts.push(context);
      pages.push(page);
    }
    
    // Measure concurrent login performance
    const startTime = Date.now();
    
    const loginPromises = pages.map(async (page, index) => {
      await page.goto('http://localhost:5173');
      await page.fill('input[placeholder*="用戶名"]', 'test@example.com');
      await page.fill('input[placeholder*="密碼"]', 'test123');
      await page.click('button:has-text("登 入")');
      await page.waitForURL(/dashboard/);
      return Date.now();
    });
    
    const completionTimes = await Promise.all(loginPromises);
    const totalTime = Math.max(...completionTimes) - startTime;
    
    console.log(`Concurrent Users: ${userCount}, Total Time: ${totalTime}ms`);
    
    // All users should complete within reasonable time
    expect(totalTime).toBeLessThan(10000); // 10 seconds for 5 concurrent users
    
    // Cleanup
    await Promise.all(contexts.map(context => context.close()));
  });

  test('should meet performance benchmarks - 5', async ({ page }) => {
    await loginAsTestUser(page);
    
    // Simulate a long session with periodic actions
    const sessionDuration = 30000; // 30 seconds
    const actionInterval = 5000; // Action every 5 seconds
    const startTime = Date.now();
    
    const performanceMetrics = [];
    
    while (Date.now() - startTime < sessionDuration) {
      // Perform an action
      await page.click('text=客戶管理');
      await page.waitForLoadState('networkidle');
      
      // Measure current performance
      const metrics = await page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        return {
          timestamp: Date.now(),
          memory: 'memory' in performance ? (performance as any).memory.usedJSHeapSize : 0,
          domNodes: document.getElementsByTagName('*').length
        };
      });
      
      performanceMetrics.push(metrics);
      
      // Go back to dashboard
      await page.click('text=儀表板');
      await page.waitForLoadState('networkidle');
      
      // Wait before next action
      await page.waitForTimeout(actionInterval);
    }
    
    // Analyze performance degradation
    const firstMetric = performanceMetrics[0];
    const lastMetric = performanceMetrics[performanceMetrics.length - 1];
    
    if (firstMetric.memory > 0 && lastMetric.memory > 0) {
      const memoryGrowth = ((lastMetric.memory - firstMetric.memory) / firstMetric.memory) * 100;
      console.log(`Memory growth over session: ${memoryGrowth.toFixed(2)}%`);
      
      // Memory growth should be minimal
      expect(memoryGrowth).toBeLessThan(20); // Less than 20% growth
    }
    
    // DOM nodes shouldn't grow excessively
    const domGrowth = lastMetric.domNodes - firstMetric.domNodes;
    console.log(`DOM node growth: ${domGrowth} nodes`);
    expect(domGrowth).toBeLessThan(1000); // Less than 1000 additional nodes
  });
});