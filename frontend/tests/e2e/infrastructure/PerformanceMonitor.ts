/**
 * Performance Monitoring System for Playwright Tests
 * Tracks Core Web Vitals, memory usage, and resource loading
 */

import { Page } from '@playwright/test';

export interface PerformanceMetrics {
  // Core Web Vitals
  lcp?: number;  // Largest Contentful Paint
  fid?: number;  // First Input Delay
  cls?: number;  // Cumulative Layout Shift
  fcp?: number;  // First Contentful Paint
  ttfb?: number; // Time to First Byte
  
  // Memory Metrics
  memoryUsage?: number;
  jsHeapSize?: number;
  domNodes?: number;
  
  // Resource Metrics
  loadTime?: number;
  domContentLoaded?: number;
  resources?: ResourceMetrics[];
  
  // Network Metrics
  requests?: number;
  failedRequests?: number;
  totalTransferSize?: number;
  
  // Custom Metrics
  longTasks?: number;
  jankScore?: number;
}

export interface ResourceMetrics {
  name: string;
  type: string;
  duration: number;
  transferSize: number;
  failed: boolean;
}

export interface PerformanceThresholds {
  lcp: number;  // < 2500ms (good), < 4000ms (needs improvement)
  fid: number;  // < 100ms (good), < 300ms (needs improvement)
  cls: number;  // < 0.1 (good), < 0.25 (needs improvement)
  loadTime: number; // < 3000ms
  memoryUsage: number; // < 100MB
}

export class PerformanceMonitor {
  private page: Page;
  private metrics: PerformanceMetrics = {};
  private thresholds: PerformanceThresholds = {
    lcp: 2500,
    fid: 100,
    cls: 0.1,
    loadTime: 3000,
    memoryUsage: 100 * 1024 * 1024, // 100MB in bytes
  };
  private startTime: number = 0;

  constructor(page: Page, customThresholds?: Partial<PerformanceThresholds>) {
    this.page = page;
    if (customThresholds) {
      this.thresholds = { ...this.thresholds, ...customThresholds };
    }
    this.attachListeners();
  }

  /**
   * Attach performance monitoring listeners
   */
  private attachListeners(): void {
    // Track page load start
    this.page.on('load', () => {
      this.collectMetrics();
    });

    // Track DOM content loaded
    this.page.on('domcontentloaded', () => {
      this.startTime = Date.now();
    });
  }

  /**
   * Collect all performance metrics
   */
  public async collectMetrics(): Promise<void> {
    // Core Web Vitals
    await this.collectCoreWebVitals();
    
    // Memory metrics
    await this.collectMemoryMetrics();
    
    // Resource metrics
    await this.collectResourceMetrics();
    
    // Network metrics
    await this.collectNetworkMetrics();
    
    // Custom metrics
    await this.collectCustomMetrics();
  }

  /**
   * Collect Core Web Vitals
   */
  private async collectCoreWebVitals(): Promise<void> {
    const vitals = await this.page.evaluate(() => {
      return new Promise<any>((resolve) => {
        const metrics: any = {};
        
        // Use Performance Observer API
        if ('PerformanceObserver' in window) {
          // LCP
          new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1] as any;
            metrics.lcp = lastEntry.renderTime || lastEntry.loadTime;
          }).observe({ entryTypes: ['largest-contentful-paint'] });

          // FID
          new PerformanceObserver((list) => {
            const entries = list.getEntries();
            if (entries.length > 0) {
              metrics.fid = (entries[0] as any).processingStart - (entries[0] as any).startTime;
            }
          }).observe({ entryTypes: ['first-input'] });

          // CLS
          let clsScore = 0;
          new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
              if (!(entry as any).hadRecentInput) {
                clsScore += (entry as any).value;
              }
            }
            metrics.cls = clsScore;
          }).observe({ entryTypes: ['layout-shift'] });

          // FCP
          const paintEntries = performance.getEntriesByType('paint');
          const fcpEntry = paintEntries.find((entry) => entry.name === 'first-contentful-paint');
          if (fcpEntry) {
            metrics.fcp = fcpEntry.startTime;
          }

          // TTFB
          const navigation = performance.getEntriesByType('navigation')[0] as any;
          if (navigation) {
            metrics.ttfb = navigation.responseStart - navigation.requestStart;
            metrics.loadTime = navigation.loadEventEnd - navigation.fetchStart;
            metrics.domContentLoaded = navigation.domContentLoadedEventEnd - navigation.fetchStart;
          }
        }

        // Wait a bit for observers to collect data
        setTimeout(() => resolve(metrics), 1000);
      });
    });

    Object.assign(this.metrics, vitals);
  }

  /**
   * Collect memory metrics
   */
  private async collectMemoryMetrics(): Promise<void> {
    const memoryMetrics = await this.page.evaluate(() => {
      const metrics: any = {};
      
      // Memory usage (Chrome only)
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        metrics.memoryUsage = memory.usedJSHeapSize;
        metrics.jsHeapSize = memory.totalJSHeapSize;
      }

      // DOM nodes count
      metrics.domNodes = document.getElementsByTagName('*').length;

      return metrics;
    });

    Object.assign(this.metrics, memoryMetrics);
  }

  /**
   * Collect resource loading metrics
   */
  private async collectResourceMetrics(): Promise<void> {
    const resources = await this.page.evaluate(() => {
      const entries = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      
      return entries.map(entry => ({
        name: entry.name,
        type: entry.initiatorType,
        duration: entry.duration,
        transferSize: entry.transferSize,
        failed: entry.transferSize === 0 && entry.duration > 0,
      }));
    });

    this.metrics.resources = resources;
  }

  /**
   * Collect network metrics
   */
  private async collectNetworkMetrics(): Promise<void> {
    const networkMetrics = await this.page.evaluate(() => {
      const entries = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      
      const metrics = {
        requests: entries.length,
        failedRequests: 0,
        totalTransferSize: 0,
      };

      entries.forEach(entry => {
        metrics.totalTransferSize += entry.transferSize;
        if (entry.transferSize === 0 && entry.duration > 0) {
          metrics.failedRequests++;
        }
      });

      return metrics;
    });

    Object.assign(this.metrics, networkMetrics);
  }

  /**
   * Collect custom metrics
   */
  private async collectCustomMetrics(): Promise<void> {
    const customMetrics = await this.page.evaluate(() => {
      const metrics: any = {};
      
      // Long tasks (tasks > 50ms)
      if ('PerformanceObserver' in window && 'PerformanceLongTaskTiming' in window) {
        let longTaskCount = 0;
        new PerformanceObserver((list) => {
          longTaskCount += list.getEntries().length;
        }).observe({ entryTypes: ['longtask'] });
        
        metrics.longTasks = longTaskCount;
      }

      // Jank score (simplified)
      const entries = performance.getEntriesByType('measure');
      let jankScore = 0;
      entries.forEach(entry => {
        if (entry.duration > 16.67) { // More than one frame (60fps)
          jankScore += (entry.duration - 16.67) / 16.67;
        }
      });
      metrics.jankScore = jankScore;

      return metrics;
    });

    Object.assign(this.metrics, customMetrics);
  }

  /**
   * Get current metrics
   */
  public async getMetrics(): Promise<PerformanceMetrics> {
    await this.collectMetrics();
    return this.metrics;
  }

  /**
   * Check if metrics meet thresholds
   */
  public checkThresholds(): {
    passed: boolean;
    failures: string[];
  } {
    const failures: string[] = [];

    if (this.metrics.lcp && this.metrics.lcp > this.thresholds.lcp) {
      failures.push(`LCP: ${this.metrics.lcp}ms > ${this.thresholds.lcp}ms`);
    }

    if (this.metrics.fid && this.metrics.fid > this.thresholds.fid) {
      failures.push(`FID: ${this.metrics.fid}ms > ${this.thresholds.fid}ms`);
    }

    if (this.metrics.cls && this.metrics.cls > this.thresholds.cls) {
      failures.push(`CLS: ${this.metrics.cls} > ${this.thresholds.cls}`);
    }

    if (this.metrics.loadTime && this.metrics.loadTime > this.thresholds.loadTime) {
      failures.push(`Load Time: ${this.metrics.loadTime}ms > ${this.thresholds.loadTime}ms`);
    }

    if (this.metrics.memoryUsage && this.metrics.memoryUsage > this.thresholds.memoryUsage) {
      const memoryMB = this.metrics.memoryUsage / 1024 / 1024;
      const thresholdMB = this.thresholds.memoryUsage / 1024 / 1024;
      failures.push(`Memory: ${memoryMB.toFixed(2)}MB > ${thresholdMB}MB`);
    }

    return {
      passed: failures.length === 0,
      failures,
    };
  }

  /**
   * Generate performance report
   */
  public generateReport(): string {
    const thresholdCheck = this.checkThresholds();
    
    return `
# Performance Report

## Core Web Vitals
- **LCP**: ${this.metrics.lcp?.toFixed(0) || 'N/A'}ms (Target: <${this.thresholds.lcp}ms)
- **FID**: ${this.metrics.fid?.toFixed(0) || 'N/A'}ms (Target: <${this.thresholds.fid}ms)
- **CLS**: ${this.metrics.cls?.toFixed(3) || 'N/A'} (Target: <${this.thresholds.cls})
- **FCP**: ${this.metrics.fcp?.toFixed(0) || 'N/A'}ms
- **TTFB**: ${this.metrics.ttfb?.toFixed(0) || 'N/A'}ms

## Load Performance
- **Total Load Time**: ${this.metrics.loadTime?.toFixed(0) || 'N/A'}ms
- **DOM Content Loaded**: ${this.metrics.domContentLoaded?.toFixed(0) || 'N/A'}ms

## Memory Usage
- **JS Heap**: ${this.metrics.memoryUsage ? (this.metrics.memoryUsage / 1024 / 1024).toFixed(2) : 'N/A'}MB
- **Total Heap**: ${this.metrics.jsHeapSize ? (this.metrics.jsHeapSize / 1024 / 1024).toFixed(2) : 'N/A'}MB
- **DOM Nodes**: ${this.metrics.domNodes || 'N/A'}

## Network
- **Total Requests**: ${this.metrics.requests || 'N/A'}
- **Failed Requests**: ${this.metrics.failedRequests || 'N/A'}
- **Transfer Size**: ${this.metrics.totalTransferSize ? (this.metrics.totalTransferSize / 1024).toFixed(2) : 'N/A'}KB

## Custom Metrics
- **Long Tasks**: ${this.metrics.longTasks || 'N/A'}
- **Jank Score**: ${this.metrics.jankScore?.toFixed(2) || 'N/A'}

## Threshold Check
**Status**: ${thresholdCheck.passed ? '✅ PASSED' : '❌ FAILED'}
${thresholdCheck.failures.length > 0 ? '\n**Failures**:\n' + thresholdCheck.failures.map(f => `- ${f}`).join('\n') : ''}

## Top Resource Load Times
${this.metrics.resources?.sort((a, b) => b.duration - a.duration).slice(0, 5).map(r => 
  `- ${r.name.split('/').pop()}: ${r.duration.toFixed(0)}ms (${(r.transferSize / 1024).toFixed(2)}KB)`
).join('\n') || 'N/A'}

---
*Generated: ${new Date().toISOString()}*
`;
  }

  /**
   * Reset metrics
   */
  public reset(): void {
    this.metrics = {};
    this.startTime = 0;
  }

  /**
   * Take performance screenshot with metrics overlay
   */
  public async capturePerformanceScreenshot(path: string): Promise<void> {
    // Inject performance overlay
    await this.page.evaluate((metrics) => {
      const overlay = document.createElement('div');
      overlay.id = 'performance-overlay';
      overlay.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 10px;
        font-family: monospace;
        font-size: 12px;
        z-index: 999999;
        border-radius: 5px;
      `;
      
      overlay.innerHTML = `
        <div><strong>Performance Metrics</strong></div>
        <div>LCP: ${metrics.lcp?.toFixed(0) || 'N/A'}ms</div>
        <div>FID: ${metrics.fid?.toFixed(0) || 'N/A'}ms</div>
        <div>CLS: ${metrics.cls?.toFixed(3) || 'N/A'}</div>
        <div>Memory: ${metrics.memoryUsage ? (metrics.memoryUsage / 1024 / 1024).toFixed(2) : 'N/A'}MB</div>
        <div>DOM Nodes: ${metrics.domNodes || 'N/A'}</div>
      `;
      
      document.body.appendChild(overlay);
    }, this.metrics);

    // Take screenshot
    await this.page.screenshot({ path, fullPage: true });

    // Remove overlay
    await this.page.evaluate(() => {
      const overlay = document.getElementById('performance-overlay');
      overlay?.remove();
    });
  }
}