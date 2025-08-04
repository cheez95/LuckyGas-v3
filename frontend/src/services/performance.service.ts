/**
 * Performance Monitoring Service
 * Tracks and reports application performance metrics
 */

interface PerformanceMetric {
  name: string;
  value: number;
  timestamp: number;
  type: 'timing' | 'resource' | 'api' | 'render' | 'custom';
  metadata?: Record<string, any>;
}

interface PerformanceReport {
  metrics: PerformanceMetric[];
  summary: {
    avgApiResponseTime: number;
    avgPageLoadTime: number;
    errorRate: number;
    totalApiCalls: number;
    slowestEndpoints: Array<{ endpoint: string; avgTime: number }>;
  };
  timestamp: number;
}

class PerformanceMonitoringService {
  private metrics: PerformanceMetric[] = [];
  private observers: Map<string, PerformanceObserver> = new Map();
  private apiCallTimings: Map<string, number[]> = new Map();
  private enabled: boolean = true;
  private bufferSize: number = 1000;
  private reportInterval: number = 60000; // 1 minute
  private reportTimer?: NodeJS.Timeout;

  constructor() {
    this.initializeMonitoring();
  }

  private initializeMonitoring() {
    if (typeof window === 'undefined' || !window.performance) {
      console.warn('Performance API not available');
      this.enabled = false;
      return;
    }

    // Monitor navigation timing
    this.observeNavigationTiming();
    
    // Monitor resource timing
    this.observeResourceTiming();
    
    // Monitor largest contentful paint
    this.observeLCP();
    
    // Monitor first input delay
    this.observeFID();
    
    // Monitor cumulative layout shift
    this.observeCLS();
    
    // Start periodic reporting
    this.startPeriodicReporting();
  }

  private observeNavigationTiming() {
    try {
      const navTiming = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      if (navTiming) {
        this.recordMetric({
          name: 'page_load_time',
          value: navTiming.loadEventEnd - navTiming.fetchStart,
          timestamp: Date.now(),
          type: 'timing',
          metadata: {
            domContentLoaded: navTiming.domContentLoadedEventEnd - navTiming.fetchStart,
            domInteractive: navTiming.domInteractive - navTiming.fetchStart,
          }
        });
      }
    } catch (error) {
      console.error('Error observing navigation timing:', error);
    }
  }

  private observeResourceTiming() {
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          const resourceEntry = entry as PerformanceResourceTiming;
          this.recordMetric({
            name: 'resource_load',
            value: resourceEntry.duration,
            timestamp: Date.now(),
            type: 'resource',
            metadata: {
              name: resourceEntry.name,
              type: resourceEntry.initiatorType,
              size: resourceEntry.transferSize,
            }
          });
        }
      });
      
      observer.observe({ entryTypes: ['resource'] });
      this.observers.set('resource', observer);
    } catch (error) {
      console.error('Error observing resource timing:', error);
    }
  }

  private observeLCP() {
    try {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        
        this.recordMetric({
          name: 'largest_contentful_paint',
          value: lastEntry.startTime,
          timestamp: Date.now(),
          type: 'timing',
          metadata: {
            element: (lastEntry as any).element?.tagName,
            url: (lastEntry as any).url,
          }
        });
      });
      
      observer.observe({ entryTypes: ['largest-contentful-paint'] });
      this.observers.set('lcp', observer);
    } catch (error) {
      console.error('Error observing LCP:', error);
    }
  }

  private observeFID() {
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.recordMetric({
            name: 'first_input_delay',
            value: entry.duration,
            timestamp: Date.now(),
            type: 'timing',
            metadata: {
              eventType: entry.name,
            }
          });
        }
      });
      
      observer.observe({ entryTypes: ['first-input'] });
      this.observers.set('fid', observer);
    } catch (error) {
      console.error('Error observing FID:', error);
    }
  }

  private observeCLS() {
    let clsValue = 0;
    const clsEntries: PerformanceEntry[] = [];

    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!(entry as any).hadRecentInput) {
            clsEntries.push(entry);
            clsValue += (entry as any).value;
          }
        }
        
        this.recordMetric({
          name: 'cumulative_layout_shift',
          value: clsValue,
          timestamp: Date.now(),
          type: 'timing',
          metadata: {
            shifts: clsEntries.length,
          }
        });
      });
      
      observer.observe({ entryTypes: ['layout-shift'] });
      this.observers.set('cls', observer);
    } catch (error) {
      console.error('Error observing CLS:', error);
    }
  }

  // Track API call performance
  trackApiCall(endpoint: string, duration: number, success: boolean, statusCode?: number) {
    if (!this.enabled) return;

    this.recordMetric({
      name: 'api_call',
      value: duration,
      timestamp: Date.now(),
      type: 'api',
      metadata: {
        endpoint,
        success,
        statusCode,
      }
    });

    // Store timing for summary
    if (!this.apiCallTimings.has(endpoint)) {
      this.apiCallTimings.set(endpoint, []);
    }
    this.apiCallTimings.get(endpoint)!.push(duration);
  }

  // Track custom performance marks
  mark(name: string, metadata?: Record<string, any>) {
    if (!this.enabled) return;

    performance.mark(name);
    this.recordMetric({
      name: `mark_${name}`,
      value: performance.now(),
      timestamp: Date.now(),
      type: 'custom',
      metadata,
    });
  }

  // Measure between two marks
  measure(name: string, startMark: string, endMark: string) {
    if (!this.enabled) return;

    try {
      performance.measure(name, startMark, endMark);
      const measure = performance.getEntriesByName(name, 'measure')[0];
      
      this.recordMetric({
        name: `measure_${name}`,
        value: measure.duration,
        timestamp: Date.now(),
        type: 'custom',
        metadata: {
          startMark,
          endMark,
        }
      });
    } catch (error) {
      console.error(`Error measuring ${name}:`, error);
    }
  }

  // Track React component render time
  trackComponentRender(componentName: string, duration: number) {
    if (!this.enabled) return;

    this.recordMetric({
      name: 'component_render',
      value: duration,
      timestamp: Date.now(),
      type: 'render',
      metadata: {
        component: componentName,
      }
    });
  }

  private recordMetric(metric: PerformanceMetric) {
    this.metrics.push(metric);
    
    // Keep buffer size under control
    if (this.metrics.length > this.bufferSize) {
      this.metrics = this.metrics.slice(-this.bufferSize);
    }
  }

  // Generate performance report
  generateReport(): PerformanceReport {
    const now = Date.now();
    const recentMetrics = this.metrics.filter(m => now - m.timestamp < this.reportInterval);
    
    // Calculate API metrics
    const apiMetrics = recentMetrics.filter(m => m.type === 'api');
    const avgApiResponseTime = apiMetrics.length > 0
      ? apiMetrics.reduce((sum, m) => sum + m.value, 0) / apiMetrics.length
      : 0;
    
    const errorRate = apiMetrics.length > 0
      ? apiMetrics.filter(m => !m.metadata?.success).length / apiMetrics.length
      : 0;

    // Calculate slowest endpoints
    const slowestEndpoints = Array.from(this.apiCallTimings.entries())
      .map(([endpoint, timings]) => ({
        endpoint,
        avgTime: timings.reduce((sum, t) => sum + t, 0) / timings.length,
      }))
      .sort((a, b) => b.avgTime - a.avgTime)
      .slice(0, 5);

    // Calculate page load metrics
    const pageLoadMetrics = recentMetrics.filter(m => m.name === 'page_load_time');
    const avgPageLoadTime = pageLoadMetrics.length > 0
      ? pageLoadMetrics.reduce((sum, m) => sum + m.value, 0) / pageLoadMetrics.length
      : 0;

    return {
      metrics: recentMetrics,
      summary: {
        avgApiResponseTime,
        avgPageLoadTime,
        errorRate,
        totalApiCalls: apiMetrics.length,
        slowestEndpoints,
      },
      timestamp: now,
    };
  }

  // Get Core Web Vitals
  getCoreWebVitals() {
    const metrics = this.metrics;
    const lcp = metrics.filter(m => m.name === 'largest_contentful_paint').pop();
    const fid = metrics.filter(m => m.name === 'first_input_delay').pop();
    const cls = metrics.filter(m => m.name === 'cumulative_layout_shift').pop();

    return {
      lcp: lcp?.value || null,
      fid: fid?.value || null,
      cls: cls?.value || null,
      timestamp: Date.now(),
    };
  }

  // Start periodic reporting
  private startPeriodicReporting() {
    this.reportTimer = setInterval(() => {
      const report = this.generateReport();
      this.sendReportToBackend(report);
    }, this.reportInterval);
  }

  // Send report to backend
  private async sendReportToBackend(report: PerformanceReport) {
    if (import.meta.env.DEV) {
      console.log('Performance Report:', report);
    }

    // In production, send to backend
    if (import.meta.env.PROD) {
      try {
        await fetch('/api/v1/monitoring/performance', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
          body: JSON.stringify(report),
        });
      } catch (error) {
        console.error('Failed to send performance report:', error);
      }
    }
  }

  // Cleanup
  destroy() {
    if (this.reportTimer) {
      clearInterval(this.reportTimer);
    }
    
    this.observers.forEach(observer => observer.disconnect());
    this.observers.clear();
    this.metrics = [];
    this.apiCallTimings.clear();
  }

  // Enable/disable monitoring
  setEnabled(enabled: boolean) {
    this.enabled = enabled;
    if (!enabled) {
      this.destroy();
    } else {
      this.initializeMonitoring();
    }
  }
}

// Export singleton instance
export const performanceMonitor = new PerformanceMonitoringService();

// React hook for performance monitoring
export const usePerformanceMonitor = () => {
  return {
    mark: (name: string, metadata?: Record<string, any>) => performanceMonitor.mark(name, metadata),
    measure: (name: string, startMark: string, endMark: string) => performanceMonitor.measure(name, startMark, endMark),
    trackComponentRender: (componentName: string, duration: number) => performanceMonitor.trackComponentRender(componentName, duration),
    generateReport: () => performanceMonitor.generateReport(),
    getCoreWebVitals: () => performanceMonitor.getCoreWebVitals(),
  };
};