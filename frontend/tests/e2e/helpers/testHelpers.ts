import { Page, expect, ConsoleMessage } from '@playwright/test';

/**
 * Test helper utilities
 */

export interface ConsoleError {
  text: string;
  type: string;
  location?: string;
  timestamp: Date;
}

export interface NetworkRequest {
  url: string;
  method: string;
  status?: number;
  duration?: number;
  timestamp: Date;
}

export interface PerformanceMetrics {
  loadTime: number;
  domContentLoaded: number;
  firstContentfulPaint?: number;
  largestContentfulPaint?: number;
  totalBlockingTime?: number;
  cumulativeLayoutShift?: number;
}

/**
 * Console error monitoring
 */
export class ConsoleMonitor {
  private errors: ConsoleError[] = [];
  private warnings: ConsoleError[] = [];
  
  constructor(page: Page) {
    page.on('console', (msg: ConsoleMessage) => {
      const error: ConsoleError = {
        text: msg.text(),
        type: msg.type(),
        location: msg.location()?.url,
        timestamp: new Date()
      };
      
      if (msg.type() === 'error') {
        this.errors.push(error);
      } else if (msg.type() === 'warning') {
        this.warnings.push(error);
      }
    });
    
    page.on('pageerror', (error: Error) => {
      this.errors.push({
        text: error.message,
        type: 'pageerror',
        timestamp: new Date()
      });
    });
  }
  
  getErrors(): ConsoleError[] {
    return this.errors;
  }
  
  getWarnings(): ConsoleError[] {
    return this.warnings;
  }
  
  hasMapErrors(): boolean {
    return this.errors.some(error => 
      error.text.includes('map is not a function') ||
      error.text.includes('Cannot read properties of undefined') ||
      error.text.includes('Cannot read property')
    );
  }
  
  clear() {
    this.errors = [];
    this.warnings = [];
  }
}

/**
 * Network request monitoring
 */
export class NetworkMonitor {
  private requests: NetworkRequest[] = [];
  private failedRequests: NetworkRequest[] = [];
  
  constructor(page: Page) {
    page.on('request', request => {
      this.requests.push({
        url: request.url(),
        method: request.method(),
        timestamp: new Date()
      });
    });
    
    page.on('response', response => {
      const request = this.requests.find(r => r.url === response.url());
      if (request) {
        request.status = response.status();
        if (response.status() >= 400) {
          this.failedRequests.push(request);
        }
      }
    });
  }
  
  getRequests(): NetworkRequest[] {
    return this.requests;
  }
  
  getFailedRequests(): NetworkRequest[] {
    return this.failedRequests;
  }
  
  getAPIRequests(): NetworkRequest[] {
    return this.requests.filter(r => 
      r.url.includes('/api/') || 
      r.url.includes('run.app')
    );
  }
  
  hasFailedAPIRequests(): boolean {
    return this.getAPIRequests().some(r => r.status && r.status >= 400);
  }
  
  clear() {
    this.requests = [];
    this.failedRequests = [];
  }
}

/**
 * Performance metrics collection
 */
export async function collectPerformanceMetrics(page: Page): Promise<PerformanceMetrics> {
  const metrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const paint = performance.getEntriesByType('paint');
    
    const fcp = paint.find(p => p.name === 'first-contentful-paint');
    const lcp = performance.getEntriesByType('largest-contentful-paint')[0];
    
    return {
      loadTime: navigation.loadEventEnd - navigation.fetchStart,
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
      firstContentfulPaint: fcp ? fcp.startTime : undefined,
      largestContentfulPaint: lcp ? lcp.startTime : undefined,
    };
  });
  
  return metrics as PerformanceMetrics;
}

/**
 * Custom assertions
 */
export async function assertNoConsoleErrors(page: Page, monitor: ConsoleMonitor) {
  const errors = monitor.getErrors();
  if (errors.length > 0) {
    const errorMessages = errors.map(e => `${e.type}: ${e.text}`).join('\n');
    throw new Error(`Console errors detected:\n${errorMessages}`);
  }
}

export async function assertNoMapErrors(monitor: ConsoleMonitor) {
  if (monitor.hasMapErrors()) {
    const mapErrors = monitor.getErrors().filter(e => 
      e.text.includes('map') || e.text.includes('undefined')
    );
    const errorMessages = mapErrors.map(e => e.text).join('\n');
    throw new Error(`Map/undefined errors detected:\n${errorMessages}`);
  }
}

export async function assertNoFailedAPIRequests(monitor: NetworkMonitor) {
  const failed = monitor.getFailedRequests();
  if (failed.length > 0) {
    const failedAPIs = failed.filter(r => 
      r.url.includes('/api/') || r.url.includes('run.app')
    );
    if (failedAPIs.length > 0) {
      const errorMessages = failedAPIs.map(r => 
        `${r.method} ${r.url} - Status: ${r.status}`
      ).join('\n');
      throw new Error(`Failed API requests:\n${errorMessages}`);
    }
  }
}

/**
 * Wait for WebSocket connection
 */
export async function waitForWebSocketConnection(page: Page, timeout: number = 10000): Promise<boolean> {
  try {
    await page.waitForFunction(
      () => {
        // Check for WebSocket in window
        return (window as any).ws?.readyState === 1 || 
               (window as any).socket?.connected === true;
      },
      { timeout }
    );
    return true;
  } catch {
    return false;
  }
}

/**
 * Take screenshot with timestamp
 */
export async function takeScreenshot(page: Page, name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  await page.screenshot({
    path: `test-results/screenshots/${name}-${timestamp}.png`,
    fullPage: true
  });
}

/**
 * Login helper
 */
export async function loginAsAdmin(page: Page) {
  await page.goto('/');
  await page.fill('input[placeholder*="用戶名"], input#username', 'admin@luckygas.com');
  await page.fill('input[type="password"]', 'admin123');
  await page.click('button[type="submit"]');
  
  // Wait for navigation
  await page.waitForURL('**/*dashboard*', { timeout: 10000 }).catch(() => {});
}

/**
 * Check responsive behavior
 */
export async function testResponsiveBehavior(page: Page, viewports: { width: number; height: number }[]) {
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.waitForTimeout(500); // Wait for resize animations
    
    // Check if key elements are still visible
    const isResponsive = await page.evaluate(() => {
      const elements = document.querySelectorAll('.ant-table, .ant-card, .ant-form');
      return Array.from(elements).every(el => {
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      });
    });
    
    expect(isResponsive).toBeTruthy();
  }
}