/**
 * Performance monitoring utilities for tracking and reporting web vitals
 */

// Dynamic import to avoid build issues
let webVitals: any = null;

export interface PerformanceMetrics {
  lcp?: number; // Largest Contentful Paint
  fid?: number; // First Input Delay
  cls?: number; // Cumulative Layout Shift
  fcp?: number; // First Contentful Paint
  ttfb?: number; // Time to First Byte
  timestamp: number;
  url: string;
  userAgent: string;
}

class PerformanceMonitor {
  private metrics: Partial<PerformanceMetrics> = {};
  private observers: PerformanceObserver[] = [];
  
  constructor() {
    this.metrics = {
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent,
    };
  }

  /**
   * Initialize performance monitoring
   */
  async init() {
    // Try to load web-vitals dynamically
    try {
      if (!webVitals) {
        webVitals = await import('web-vitals');
      }
      
      // Capture Core Web Vitals
      webVitals.getCLS?.(metric => {
        this.metrics.cls = metric.value;
        this.reportMetric('CLS', metric.value);
      });
      
      webVitals.getFID?.(metric => {
        this.metrics.fid = metric.value;
        this.reportMetric('FID', metric.value);
      });
      
      webVitals.getLCP?.(metric => {
        this.metrics.lcp = metric.value;
        this.reportMetric('LCP', metric.value);
      });
      
      webVitals.getFCP?.(metric => {
        this.metrics.fcp = metric.value;
        this.reportMetric('FCP', metric.value);
      });
      
      webVitals.getTTFB?.(metric => {
        this.metrics.ttfb = metric.value;
        this.reportMetric('TTFB', metric.value);
      });
    } catch (error) {
      console.warn('Web vitals monitoring not available:', error);
    }

    // Monitor long tasks
    this.observeLongTasks();
    
    // Monitor resource timing
    this.observeResourceTiming();
    
    // Monitor navigation timing
    this.reportNavigationTiming();
  }

  /**
   * Observe long tasks that block the main thread
   */
  private observeLongTasks() {
    if ('PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.duration > 50) { // Tasks longer than 50ms
              console.warn('Long task detected:', {
                duration: entry.duration,
                startTime: entry.startTime,
                name: entry.name,
              });
            }
          }
        });
        
        observer.observe({ entryTypes: ['longtask'] });
        this.observers.push(observer);
      } catch (e) {
        console.error('Failed to observe long tasks:', e);
      }
    }
  }

  /**
   * Monitor resource loading performance
   */
  private observeResourceTiming() {
    if ('PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          for (const entry of list.getEntries() as PerformanceResourceTiming[]) {
            // Report slow resources
            if (entry.duration > 1000) {
              console.warn('Slow resource:', {
                name: entry.name,
                duration: entry.duration,
                type: entry.initiatorType,
                size: entry.transferSize,
              });
            }
          }
        });
        
        observer.observe({ entryTypes: ['resource'] });
        this.observers.push(observer);
      } catch (e) {
        console.error('Failed to observe resource timing:', e);
      }
    }
  }

  /**
   * Report navigation timing metrics
   */
  private reportNavigationTiming() {
    if (window.performance && window.performance.timing) {
      const timing = window.performance.timing;
      const navigationStart = timing.navigationStart;
      
      // Calculate key metrics
      const metrics = {
        domContentLoaded: timing.domContentLoadedEventEnd - navigationStart,
        loadComplete: timing.loadEventEnd - navigationStart,
        domInteractive: timing.domInteractive - navigationStart,
        dnsLookup: timing.domainLookupEnd - timing.domainLookupStart,
        tcpConnection: timing.connectEnd - timing.connectStart,
        request: timing.responseStart - timing.requestStart,
        response: timing.responseEnd - timing.responseStart,
        domProcessing: timing.domComplete - timing.domLoading,
      };
      
      console.log('Navigation Timing:', metrics);
      
      // Check against performance budgets
      if (metrics.loadComplete > 3000) {
        console.warn('⚠️ Page load exceeds 3s target:', metrics.loadComplete + 'ms');
      }
      
      if (metrics.domContentLoaded > 1500) {
        console.warn('⚠️ DOM content loaded exceeds 1.5s:', metrics.domContentLoaded + 'ms');
      }
    }
  }

  /**
   * Report a performance metric
   */
  private reportMetric(name: string, value: number) {
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      const emoji = this.getMetricEmoji(name, value);
      console.log(`${emoji} ${name}: ${value.toFixed(2)}ms`);
    }
    
    // Send to analytics in production
    if (process.env.NODE_ENV === 'production') {
      this.sendToAnalytics(name, value);
    }
  }

  /**
   * Get emoji indicator for metric quality
   */
  private getMetricEmoji(name: string, value: number): string {
    const thresholds: { [key: string]: { good: number; needs_improvement: number } } = {
      LCP: { good: 2500, needs_improvement: 4000 },
      FID: { good: 100, needs_improvement: 300 },
      CLS: { good: 0.1, needs_improvement: 0.25 },
      FCP: { good: 1800, needs_improvement: 3000 },
      TTFB: { good: 600, needs_improvement: 1000 },
    };
    
    const threshold = thresholds[name];
    if (!threshold) return '📊';
    
    if (value <= threshold.good) return '✅';
    if (value <= threshold.needs_improvement) return '⚠️';
    return '❌';
  }

  /**
   * Send metrics to analytics service
   */
  private sendToAnalytics(name: string, value: number) {
    // Implement your analytics service integration here
    // Example: Google Analytics, Sentry, custom endpoint
    const payload = {
      metric: name,
      value: value,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent,
    };
    
    // Send to your analytics endpoint
    // fetch('/api/v1/analytics/performance', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(payload),
    // }).catch(err => console.error('Failed to send metrics:', err));
  }

  /**
   * Get current performance metrics
   */
  getMetrics(): Partial<PerformanceMetrics> {
    return { ...this.metrics };
  }

  /**
   * Cleanup observers
   */
  cleanup() {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
  }
}

// Singleton instance
let performanceMonitor: PerformanceMonitor | null = null;

/**
 * Initialize performance monitoring
 */
export function initPerformanceMonitoring() {
  if (!performanceMonitor) {
    performanceMonitor = new PerformanceMonitor();
    performanceMonitor.init();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      performanceMonitor?.cleanup();
    });
  }
  
  return performanceMonitor;
}

/**
 * Measure component render performance
 */
export function measureComponentPerformance(componentName: string) {
  const startTime = performance.now();
  
  return {
    end: () => {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      if (duration > 16) { // More than one frame (16ms)
        console.warn(`⚠️ Slow component render: ${componentName} took ${duration.toFixed(2)}ms`);
      }
      
      return duration;
    }
  };
}

/**
 * Debounce function for performance optimization
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate = false
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return function(this: any, ...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      if (!immediate) func.apply(this, args);
    };
    
    const callNow = immediate && !timeout;
    
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    
    if (callNow) func.apply(this, args);
  };
}

/**
 * Throttle function for performance optimization
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false;
  
  return function(this: any, ...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Lazy load images with Intersection Observer
 */
export function lazyLoadImages(selector = 'img[data-lazy]') {
  if ('IntersectionObserver' in window) {
    const images = document.querySelectorAll(selector);
    
    const imageObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target as HTMLImageElement;
          const src = img.dataset.src;
          
          if (src) {
            img.src = src;
            img.removeAttribute('data-lazy');
            imageObserver.unobserve(img);
          }
        }
      });
    });
    
    images.forEach(img => imageObserver.observe(img));
  }
}

export default {
  initPerformanceMonitoring,
  measureComponentPerformance,
  debounce,
  throttle,
  lazyLoadImages,
};