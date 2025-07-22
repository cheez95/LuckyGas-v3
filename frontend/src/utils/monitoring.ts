/**
 * Frontend monitoring and error tracking setup
 * Includes Sentry integration and performance monitoring
 */

import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';
import { CaptureConsole } from '@sentry/integrations';

interface MonitoringConfig {
  dsn?: string;
  environment?: string;
  release?: string;
  tracesSampleRate?: number;
  enabled?: boolean;
}

class MonitoringService {
  private initialized: boolean = false;
  private performanceObserver?: PerformanceObserver;

  /**
   * Initialize Sentry monitoring
   */
  init(config: MonitoringConfig = {}) {
    const {
      dsn = import.meta.env.VITE_SENTRY_DSN,
      environment = import.meta.env.VITE_APP_ENV || 'development',
      release = import.meta.env.VITE_APP_VERSION || 'unknown',
      tracesSampleRate = environment === 'production' ? 0.1 : 1.0,
      enabled = environment !== 'development',
    } = config;

    if (!enabled || !dsn) {
      console.log('Monitoring disabled or DSN not configured');
      return;
    }

    Sentry.init({
      dsn,
      environment,
      release,
      tracesSampleRate,
      integrations: [
        new BrowserTracing({
          // Set tracingOrigins to control what URLs are traced
          tracingOrigins: ['localhost', 'luckygas.tw', /^\//],
          // Track route changes
          routingInstrumentation: Sentry.reactRouterV6Instrumentation(
            React.useEffect,
            useLocation,
            useNavigationType,
            createRoutesFromChildren,
            matchRoutes
          ),
        }),
        new CaptureConsole({
          levels: ['error', 'warn'],
        }),
      ],
      // Performance Monitoring
      beforeSend: this.beforeSend,
      // Filter out noise
      ignoreErrors: [
        // Browser extensions
        'top.GLOBALS',
        // Random network errors
        'Network request failed',
        'NetworkError',
        'Failed to fetch',
        // User cancelled
        'Non-Error promise rejection captured',
        // PWA errors
        'ResizeObserver loop limit exceeded',
      ],
      // Privacy settings
      autoSessionTracking: true,
      // Don't send PII
      beforeBreadcrumb: this.beforeBreadcrumb,
    });

    this.initialized = true;
    this.initPerformanceMonitoring();
    console.log('Monitoring initialized');
  }

  /**
   * Filter sensitive data before sending to Sentry
   */
  private beforeSend(event: Sentry.Event, hint?: Sentry.EventHint): Sentry.Event | null {
    // Filter out sensitive data from URLs
    if (event.request?.url) {
      event.request.url = this.sanitizeUrl(event.request.url);
    }

    // Filter out sensitive headers
    if (event.request?.headers) {
      const sensitiveHeaders = ['authorization', 'cookie', 'x-api-key'];
      sensitiveHeaders.forEach(header => {
        if (event.request?.headers?.[header]) {
          event.request.headers[header] = '[FILTERED]';
        }
      });
    }

    // Filter out sensitive form data
    if (event.extra?.formData) {
      const sensitiveFields = ['password', 'creditCard', 'ssn', 'phone'];
      sensitiveFields.forEach(field => {
        if (event.extra?.formData[field]) {
          event.extra.formData[field] = '[FILTERED]';
        }
      });
    }

    return event;
  }

  /**
   * Filter breadcrumbs before recording
   */
  private beforeBreadcrumb(breadcrumb: Sentry.Breadcrumb): Sentry.Breadcrumb | null {
    // Filter out noisy console logs
    if (breadcrumb.category === 'console' && breadcrumb.level === 'log') {
      return null;
    }

    // Filter sensitive data from fetch/xhr breadcrumbs
    if (breadcrumb.category === 'fetch' || breadcrumb.category === 'xhr') {
      if (breadcrumb.data?.url) {
        breadcrumb.data.url = this.sanitizeUrl(breadcrumb.data.url);
      }
    }

    return breadcrumb;
  }

  /**
   * Sanitize URLs to remove sensitive data
   */
  private sanitizeUrl(url: string): string {
    try {
      const urlObj = new URL(url);
      // Remove sensitive query params
      const sensitiveParams = ['token', 'api_key', 'secret', 'password'];
      sensitiveParams.forEach(param => {
        if (urlObj.searchParams.has(param)) {
          urlObj.searchParams.set(param, '[FILTERED]');
        }
      });
      return urlObj.toString();
    } catch {
      return url;
    }
  }

  /**
   * Initialize performance monitoring
   */
  private initPerformanceMonitoring() {
    if (!('PerformanceObserver' in window)) {
      return;
    }

    // Monitor Core Web Vitals
    this.performanceObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        // Send to Sentry as custom metrics
        if (entry.entryType === 'largest-contentful-paint') {
          this.trackMetric('lcp', (entry as any).renderTime || (entry as any).loadTime);
        } else if (entry.entryType === 'first-input') {
          this.trackMetric('fid', (entry as any).processingStart - entry.startTime);
        } else if (entry.entryType === 'layout-shift') {
          this.trackMetric('cls', (entry as any).value);
        }
      }
    });

    // Observe different performance metrics
    try {
      this.performanceObserver.observe({ entryTypes: ['largest-contentful-paint'] });
      this.performanceObserver.observe({ entryTypes: ['first-input'] });
      this.performanceObserver.observe({ entryTypes: ['layout-shift'] });
    } catch (e) {
      console.warn('Failed to observe performance metrics', e);
    }
  }

  /**
   * Track custom metrics
   */
  trackMetric(name: string, value: number, unit: string = 'none') {
    if (!this.initialized) return;

    const transaction = Sentry.getCurrentHub().getScope()?.getTransaction();
    if (transaction) {
      transaction.setMeasurement(name, value, unit);
    }
  }

  /**
   * Track custom events
   */
  trackEvent(eventName: string, data?: Record<string, any>) {
    if (!this.initialized) return;

    Sentry.addBreadcrumb({
      category: 'custom',
      message: eventName,
      level: 'info',
      data,
    });
  }

  /**
   * Track user actions
   */
  trackUserAction(action: string, data?: Record<string, any>) {
    this.trackEvent(`user.${action}`, data);
  }

  /**
   * Set user context
   */
  setUser(user: { id: string; email?: string; role?: string } | null) {
    if (!this.initialized) return;

    if (user) {
      Sentry.setUser({
        id: user.id,
        email: user.email,
        // Don't send other PII
        ip_address: undefined,
      });
      Sentry.setTag('user.role', user.role || 'unknown');
    } else {
      Sentry.setUser(null);
    }
  }

  /**
   * Track API errors
   */
  trackApiError(
    endpoint: string,
    method: string,
    status: number,
    error?: any
  ) {
    if (!this.initialized) return;

    Sentry.withScope((scope) => {
      scope.setTag('api.endpoint', endpoint);
      scope.setTag('api.method', method);
      scope.setTag('api.status', status);
      scope.setContext('api', {
        endpoint,
        method,
        status,
        error: error?.message || 'Unknown error',
      });

      Sentry.captureException(
        new Error(`API Error: ${method} ${endpoint} - ${status}`),
        {
          level: status >= 500 ? 'error' : 'warning',
        }
      );
    });
  }

  /**
   * Track WebSocket errors
   */
  trackWebSocketError(event: string, error: any) {
    if (!this.initialized) return;

    Sentry.withScope((scope) => {
      scope.setTag('websocket.event', event);
      scope.setContext('websocket', {
        event,
        error: error?.message || 'Unknown error',
      });

      Sentry.captureException(
        new Error(`WebSocket Error: ${event}`),
        {
          level: 'error',
        }
      );
    });
  }

  /**
   * Profile a function's performance
   */
  async profile<T>(
    name: string,
    fn: () => Promise<T>,
    tags?: Record<string, string>
  ): Promise<T> {
    if (!this.initialized) {
      return fn();
    }

    const transaction = Sentry.startTransaction({
      name,
      op: 'function',
      tags,
    });

    Sentry.getCurrentHub().configureScope((scope) => scope.setSpan(transaction));

    try {
      const result = await fn();
      transaction.setStatus('ok');
      return result;
    } catch (error) {
      transaction.setStatus('internal_error');
      throw error;
    } finally {
      transaction.finish();
    }
  }

  /**
   * Cleanup monitoring
   */
  cleanup() {
    if (this.performanceObserver) {
      this.performanceObserver.disconnect();
    }
  }
}

// Export singleton instance
export const monitoring = new MonitoringService();

// React error boundary integration
export const MonitoringErrorBoundary = Sentry.ErrorBoundary;

// React profiler integration
export const MonitoringProfiler = Sentry.Profiler;

// Hook for tracking component renders
export function useMonitoringProfiler(name: string) {
  React.useEffect(() => {
    monitoring.trackEvent('component.render', { name });
  }, [name]);
}

// Hook for tracking route changes
export function useRouteMonitoring(routeName: string) {
  React.useEffect(() => {
    monitoring.trackEvent('route.change', { route: routeName });
    Sentry.setTag('route', routeName);
  }, [routeName]);
}

// Missing imports for Sentry router instrumentation
import React from 'react';
import { 
  useLocation, 
  useNavigationType,
  createRoutesFromChildren,
  matchRoutes
} from 'react-router-dom';