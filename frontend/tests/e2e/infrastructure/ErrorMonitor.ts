/**
 * Comprehensive Error Monitoring System for Playwright Tests
 * Captures, categorizes, and analyzes console errors with intelligent fix generation
 */

import { ConsoleMessage, Page } from '@playwright/test';

export enum ErrorSeverity {
  CRITICAL = 'critical', // App crash, blank screen, data loss
  HIGH = 'high',         // Functional failures, broken features
  MEDIUM = 'medium',     // Performance issues, UX problems
  LOW = 'low',           // Warnings, deprecations
}

export enum ErrorCategory {
  JAVASCRIPT = 'javascript',
  NETWORK = 'network',
  SECURITY = 'security',
  PERFORMANCE = 'performance',
  RESOURCE = 'resource',
  VALIDATION = 'validation',
  WEBSOCKET = 'websocket',
  API = 'api',
}

export interface ErrorContext {
  url: string;
  timestamp: Date;
  userAction?: string;
  browserInfo: string;
  stackTrace?: string;
  networkRequests?: string[];
  performanceMetrics?: any;
  sessionId: string;
}

export interface CapturedError {
  message: string;
  type: ConsoleMessage['type'];
  severity: ErrorSeverity;
  category: ErrorCategory;
  context: ErrorContext;
  frequency: number;
  firstSeen: Date;
  lastSeen: Date;
  hash: string;
  fixSuggestion?: string;
  autoFixable: boolean;
}

export interface ErrorPattern {
  pattern: RegExp;
  category: ErrorCategory;
  severity: ErrorSeverity;
  fixTemplate?: string;
  autoFixable: boolean;
}

export class ErrorMonitor {
  private errors: Map<string, CapturedError> = new Map();
  private page: Page;
  private sessionId: string;
  private currentUserAction: string = '';
  
  // Error patterns for categorization
  private errorPatterns: ErrorPattern[] = [
    // JavaScript Errors
    {
      pattern: /TypeError|ReferenceError|SyntaxError/i,
      category: ErrorCategory.JAVASCRIPT,
      severity: ErrorSeverity.HIGH,
      fixTemplate: 'Add null checks and type validation',
      autoFixable: true,
    },
    {
      pattern: /Cannot read prop(erty|erties) .* of (undefined|null)/i,
      category: ErrorCategory.JAVASCRIPT,
      severity: ErrorSeverity.HIGH,
      fixTemplate: 'Add optional chaining (?.) or default values',
      autoFixable: true,
    },
    
    // Network Errors
    {
      pattern: /Failed to fetch|NetworkError|ERR_NETWORK/i,
      category: ErrorCategory.NETWORK,
      severity: ErrorSeverity.HIGH,
      fixTemplate: 'Add retry logic with exponential backoff',
      autoFixable: true,
    },
    {
      pattern: /404|Not Found/i,
      category: ErrorCategory.API,
      severity: ErrorSeverity.HIGH,
      fixTemplate: 'Verify API endpoint exists and URL construction',
      autoFixable: false,
    },
    {
      pattern: /CORS|Cross-Origin/i,
      category: ErrorCategory.SECURITY,
      severity: ErrorSeverity.CRITICAL,
      fixTemplate: 'Update backend CORS configuration',
      autoFixable: false,
    },
    
    // Security Errors
    {
      pattern: /Mixed Content|insecure/i,
      category: ErrorCategory.SECURITY,
      severity: ErrorSeverity.CRITICAL,
      fixTemplate: 'Enforce HTTPS for all resources',
      autoFixable: true,
    },
    {
      pattern: /CSP|Content Security Policy/i,
      category: ErrorCategory.SECURITY,
      severity: ErrorSeverity.HIGH,
      fixTemplate: 'Update CSP headers or inline script handling',
      autoFixable: false,
    },
    
    // Performance Issues
    {
      pattern: /slow|timeout|exceeded|memory leak/i,
      category: ErrorCategory.PERFORMANCE,
      severity: ErrorSeverity.MEDIUM,
      fixTemplate: 'Optimize component rendering and memory management',
      autoFixable: true,
    },
    {
      pattern: /Long task|blocked main thread/i,
      category: ErrorCategory.PERFORMANCE,
      severity: ErrorSeverity.MEDIUM,
      fixTemplate: 'Move heavy computations to Web Workers',
      autoFixable: true,
    },
    
    // WebSocket Errors
    {
      pattern: /WebSocket|ws:|wss:|connection closed/i,
      category: ErrorCategory.WEBSOCKET,
      severity: ErrorSeverity.MEDIUM,
      fixTemplate: 'Implement reconnection logic with backoff',
      autoFixable: true,
    },
    
    // Resource Loading
    {
      pattern: /Failed to load resource|404.*\.(js|css|png|jpg)/i,
      category: ErrorCategory.RESOURCE,
      severity: ErrorSeverity.MEDIUM,
      fixTemplate: 'Verify asset paths and build configuration',
      autoFixable: false,
    },
    
    // Validation Errors
    {
      pattern: /validation|invalid|required field/i,
      category: ErrorCategory.VALIDATION,
      severity: ErrorSeverity.LOW,
      fixTemplate: 'Add proper form validation and error messages',
      autoFixable: true,
    },
  ];

  constructor(page: Page) {
    this.page = page;
    this.sessionId = this.generateSessionId();
    this.attachListeners();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private attachListeners(): void {
    // Console message listener
    this.page.on('console', (msg) => this.handleConsoleMessage(msg));
    
    // Page error listener (uncaught exceptions)
    this.page.on('pageerror', (error) => this.handlePageError(error));
    
    // Request failed listener
    this.page.on('requestfailed', (request) => this.handleRequestFailed(request));
    
    // Response listener for HTTP errors
    this.page.on('response', (response) => this.handleResponse(response));
  }

  private async handleConsoleMessage(msg: ConsoleMessage): Promise<void> {
    const type = msg.type();
    if (type === 'error' || type === 'warning') {
      const text = msg.text();
      const location = msg.location();
      
      const error = await this.categorizeError(text, type);
      error.context.stackTrace = location ? 
        `${location.url}:${location.lineNumber}:${location.columnNumber}` : 
        undefined;
      
      this.addError(error);
    }
  }

  private async handlePageError(error: Error): Promise<void> {
    const categorizedError = await this.categorizeError(
      error.message + '\n' + error.stack,
      'error'
    );
    categorizedError.severity = ErrorSeverity.CRITICAL;
    this.addError(categorizedError);
  }

  private async handleRequestFailed(request: any): Promise<void> {
    const failure = request.failure();
    if (failure) {
      const error = await this.categorizeError(
        `Request failed: ${request.url()} - ${failure.errorText}`,
        'error'
      );
      error.category = ErrorCategory.NETWORK;
      this.addError(error);
    }
  }

  private async handleResponse(response: any): Promise<void> {
    const status = response.status();
    if (status >= 400) {
      const error = await this.categorizeError(
        `HTTP ${status}: ${response.url()}`,
        'error'
      );
      error.category = ErrorCategory.API;
      error.severity = status >= 500 ? ErrorSeverity.CRITICAL : ErrorSeverity.HIGH;
      this.addError(error);
    }
  }

  private async categorizeError(message: string, type: string): Promise<CapturedError> {
    // Find matching pattern
    const match = this.errorPatterns.find(p => p.pattern.test(message));
    
    // Create context
    const context: ErrorContext = {
      url: this.page.url(),
      timestamp: new Date(),
      userAction: this.currentUserAction,
      browserInfo: await this.getBrowserInfo(),
      sessionId: this.sessionId,
      performanceMetrics: await this.getPerformanceMetrics(),
    };

    // Create error object
    const error: CapturedError = {
      message,
      type: type as any,
      severity: match?.severity || ErrorSeverity.LOW,
      category: match?.category || ErrorCategory.JAVASCRIPT,
      context,
      frequency: 1,
      firstSeen: new Date(),
      lastSeen: new Date(),
      hash: this.hashError(message),
      fixSuggestion: match?.fixTemplate,
      autoFixable: match?.autoFixable || false,
    };

    return error;
  }

  private hashError(message: string): string {
    // Simple hash for deduplication
    let hash = 0;
    for (let i = 0; i < message.length; i++) {
      const char = message.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash.toString(36);
  }

  private addError(error: CapturedError): void {
    const existing = this.errors.get(error.hash);
    if (existing) {
      existing.frequency++;
      existing.lastSeen = new Date();
    } else {
      this.errors.set(error.hash, error);
    }
  }

  private async getBrowserInfo(): Promise<string> {
    return await this.page.evaluate(() => navigator.userAgent);
  }

  private async getPerformanceMetrics(): Promise<any> {
    return await this.page.evaluate(() => {
      const perf = performance as any;
      const memory = perf.memory || {};
      const navigation = performance.getEntriesByType('navigation')[0] as any;
      
      return {
        memory: {
          usedJSHeapSize: memory.usedJSHeapSize,
          totalJSHeapSize: memory.totalJSHeapSize,
          jsHeapSizeLimit: memory.jsHeapSizeLimit,
        },
        timing: navigation ? {
          domContentLoaded: navigation.domContentLoadedEventEnd,
          loadComplete: navigation.loadEventEnd,
          responseTime: navigation.responseEnd - navigation.requestStart,
        } : null,
      };
    });
  }

  public setUserAction(action: string): void {
    this.currentUserAction = action;
  }

  public getErrors(): CapturedError[] {
    return Array.from(this.errors.values());
  }

  public getErrorsBySeverity(severity: ErrorSeverity): CapturedError[] {
    return this.getErrors().filter(e => e.severity === severity);
  }

  public getErrorsByCategory(category: ErrorCategory): CapturedError[] {
    return this.getErrors().filter(e => e.category === category);
  }

  public getCriticalErrors(): CapturedError[] {
    return this.getErrorsBySeverity(ErrorSeverity.CRITICAL);
  }

  public getAutoFixableErrors(): CapturedError[] {
    return this.getErrors().filter(e => e.autoFixable);
  }

  public getErrorSummary(): {
    total: number;
    bySeverity: Record<ErrorSeverity, number>;
    byCategory: Record<ErrorCategory, number>;
    autoFixable: number;
    criticalCount: number;
  } {
    const errors = this.getErrors();
    const summary = {
      total: errors.length,
      bySeverity: {} as Record<ErrorSeverity, number>,
      byCategory: {} as Record<ErrorCategory, number>,
      autoFixable: 0,
      criticalCount: 0,
    };

    // Initialize counts
    Object.values(ErrorSeverity).forEach(s => summary.bySeverity[s] = 0);
    Object.values(ErrorCategory).forEach(c => summary.byCategory[c] = 0);

    // Count errors
    errors.forEach(error => {
      summary.bySeverity[error.severity]++;
      summary.byCategory[error.category]++;
      if (error.autoFixable) summary.autoFixable++;
      if (error.severity === ErrorSeverity.CRITICAL) summary.criticalCount++;
    });

    return summary;
  }

  public generateReport(): string {
    const summary = this.getErrorSummary();
    const errors = this.getErrors();
    
    let report = `
# Error Monitoring Report
Session: ${this.sessionId}
Generated: ${new Date().toISOString()}

## Summary
- Total Errors: ${summary.total}
- Critical Errors: ${summary.criticalCount}
- Auto-fixable: ${summary.autoFixable}

## By Severity
${Object.entries(summary.bySeverity).map(([sev, count]) => 
  `- ${sev}: ${count}`).join('\n')}

## By Category
${Object.entries(summary.byCategory).map(([cat, count]) => 
  `- ${cat}: ${count}`).join('\n')}

## Error Details
${errors.map(error => `
### ${error.severity.toUpperCase()}: ${error.category}
- Message: ${error.message}
- URL: ${error.context.url}
- Frequency: ${error.frequency}
- First Seen: ${error.firstSeen.toISOString()}
- Last Seen: ${error.lastSeen.toISOString()}
- Auto-fixable: ${error.autoFixable}
- Fix Suggestion: ${error.fixSuggestion || 'Manual review required'}
${error.context.stackTrace ? `- Stack: ${error.context.stackTrace}` : ''}
`).join('\n')}
`;
    
    return report;
  }

  public reset(): void {
    this.errors.clear();
    this.currentUserAction = '';
  }
}